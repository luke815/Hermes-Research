"""Score the three weekly-round cells on the full panel, not the train cache.

Cells as written in research/generated.md items 25, 26 and 27, commit
14e6cba. The indicator cache the sweep wrote ends at the train cutoff, so
scoring from it reports empty held-out periods. This reads the panel files
for the same 234 names, rebuilds each measure the way regime_tester/indicators.py
builds it, applies the registered transform, and lags it one bar.

rel_3 and rel_1 equal ret_3 and ret_1 inside a same-day rank: subtracting
BTC's return from every name on one date cancels in the spread, so the
spread scored is the absolute one and the payload says so. The net is the
sweep's own, the thin-tier round trip, with no funding carry, because the
panel has no USD open interest for the live names.

A price, basis or long/short change after day t must leave the signal at t
unchanged, and that check is in the results file. This does not pull and it
does not write a confirmation row.
"""

import json
import os
import sys

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from ta.trend import WMAIndicator  # noqa: E402

from regime_tester.confirm import (  # noqa: E402
    TEST_START, TRAIN_END, VALIDATION_END, VALIDATION_START,
)
from regime_tester.factors import build_factors  # noqa: E402
from regime_tester.heat import COMPONENTS  # noqa: E402
from regime_tester.pit import apply_listing_mask  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402
from regime_tester.vectorized import transform_column, transform_matrix  # noqa: E402

CACHE = "data/panel_xs_cache/indicators_91ee884150ff50aa_4953200eab4e_v3.csv"
PANEL_XS = "data/panel_xs_laevitas"
PANEL = "data/panel.csv"
PREREG = "14e6cba8e0e0b9ab23050e1cfe19d2d9b1d6507c"
COST = 2 * 15 / 10_000
MIN_NAMES = 20
MIN_INDEPENDENT = 40
T_BAR = 2.0
PERIODS = (
    ("train", "2010-01-01", str(TRAIN_END.date())),
    ("validation", str(VALIDATION_START.date()), str(VALIDATION_END.date())),
    ("test", str(TEST_START.date()), "9999-12-31"),
)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CELLS = (
    {
        "item": "W25",
        "name": "w25_ls_ratio_chg_7",
        "cell": "ls_ratio_chg_7|xs_rank|above|90|rel_3|pit_cross_section|none|daily",
        "measure": "ls_ratio_chg_7",
        "column": "long_short_ratio",
        "transform": "xs_rank",
        "direction": "above",
        "threshold": 90.0,
        "horizon": 3,
        "target_note": (
            "rel_3 equals ret_3 inside a same-day rank: subtracting BTC's "
            "return from every name on one date cancels in the spread"
        ),
    },
    {
        "item": "W26",
        "name": "w26_basis_chg_7",
        "cell": "basis_chg_7|xs_rank|below|10|rel_1|pit_cross_section|none|daily",
        "measure": "basis_chg_7",
        "column": "basis",
        "transform": "xs_rank",
        "direction": "below",
        "threshold": 10.0,
        "horizon": 1,
        "target_note": (
            "rel_1 equals ret_1 inside a same-day rank: subtracting BTC's "
            "return from every name on one date cancels in the spread"
        ),
    },
    {
        "item": "W27",
        "name": "w27_wma_20",
        "cell": "wma_20|chg_3|above|95|ret_1|pit_cross_section|none|daily",
        "measure": "wma_20",
        "column": "close",
        "transform": "chg_3",
        "direction": "above",
        "threshold": 95.0,
        "horizon": 1,
        "target_note": "ret_1 is the absolute forward return, as registered",
    },
)


def names_from_cache():
    """The 234 names the train row was scored on, taken from the cache header."""
    wide = pd.read_csv(os.path.join(ROOT, CACHE), header=[0, 1], index_col=0, nrows=0)
    return list(wide["roc_12"].columns)


def load_columns(names):
    frames = []
    for name in names:
        path = os.path.join(ROOT, PANEL_XS, name + ".csv")
        frame = pd.read_csv(path, usecols=["date", "close", "basis", "long_short_ratio"])
        frame["date"] = pd.to_datetime(frame["date"], utc=True)
        frame = frame.set_index("date").astype(float).sort_index()
        frame.columns = pd.MultiIndex.from_product([frame.columns, [name]])
        frames.append(frame)
    return pd.concat(frames, axis=1).sort_index()


def measure_of(raw, spec):
    """The library's definition: a 7-day difference, or the 20-day WMA."""
    column = raw[spec["column"]]
    if spec["measure"] == "wma_20":
        out = {}
        for name in column.columns:
            series = column[name].dropna()
            out[name] = pd.Series(
                WMAIndicator(series, 20).wma().to_numpy(), index=series.index)
        return pd.DataFrame(out).reindex(column.index)
    return column.diff(7)


def spans_for(columns):
    from scripts.sweep_xs import panel_spans
    return panel_spans(columns)


def daily_spread(cut, net, spans, spec):
    """Flagged minus the rest, at the registered cut of the lagged feature."""
    masked = apply_listing_mask(cut.reindex(columns=net.columns), spans)
    values = masked.to_numpy(dtype=float)
    returns = net.to_numpy(dtype=float)
    out = np.full(len(values), np.nan)
    for i in range(len(values)):
        both = ~np.isnan(values[i]) & ~np.isnan(returns[i])
        if both.sum() < MIN_NAMES:
            continue
        present = values[i][both]
        if spec["direction"] == "above":
            flagged = present >= spec["threshold"]
        else:
            flagged = present <= spec["threshold"]
        if flagged.sum() < 2 or (~flagged).sum() < 2:
            continue
        got = returns[i][both]
        out[i] = got[flagged].mean() - got[~flagged].mean()
    return pd.Series(out, index=cut.index)


def block(spread, start, end, horizon):
    part = spread[(spread.index >= start) & (spread.index <= end)].dropna()
    if part.empty:
        return {"spread_independent": None, "n_independent": 0, "t": None,
                "n_overlap": 0}
    independent = part.iloc[::horizon]
    t_stat = None
    if len(independent) > 2 and independent.std() > 0:
        t_stat = float(independent.mean() / (independent.std() / np.sqrt(len(independent))))
    return {
        "spread_independent": float(independent.mean()),
        "n_independent": int(len(independent)),
        "t": t_stat,
        "n_overlap": int(len(part)),
    }


def verdict(periods, train_sign):
    held = [periods[name] for name in ("validation", "test")]
    if any(row["n_independent"] < MIN_INDEPENDENT for row in held):
        return "insufficient", "a held-out period holds fewer than 40 independent dates"
    signs = []
    for row in held:
        spread = row["spread_independent"]
        signs.append(0 if spread is None else (spread > 0) - (spread < 0))
    if any(sign != train_sign for sign in signs):
        return "rejected", "a held-out period flips the train sign"
    if any(row["t"] is None or abs(row["t"]) < T_BAR for row in held):
        return "rejected", "a held-out non-overlapping t-stat does not reach 2"
    return "kept", "the spread keeps its sign and the t-stat reaches 2 in both held-out periods"


def feature(raw, spec):
    built = measure_of(raw, spec)
    if spec["transform"] == "xs_rank":
        transformed = transform_matrix(built, "xs_rank")
    else:
        transformed = pd.DataFrame(
            {col: transform_column(built[col].to_numpy(dtype=float), spec["transform"])
             for col in built.columns},
            index=built.index)
    return transformed.shift(1)


def lookahead(raw, spec):
    """Perturb the raw input after the midpoint and check the signal there is unchanged."""
    column = raw[spec["column"]]
    name = column.columns[0]
    series = column[name].dropna()
    t = len(series) // 2
    single = raw.loc[series.index, (slice(None), name)]
    single.columns = single.columns.droplevel(1)
    base = feature(single, spec)[name]
    perturbed = single.copy()
    perturbed.iloc[t + 1:, perturbed.columns.get_loc(spec["column"])] += 1.0
    other = feature(perturbed, spec)[name]
    left = base.iloc[:t + 1].to_numpy(dtype=float)
    right = other.iloc[:t + 1].to_numpy(dtype=float)
    return bool(np.allclose(np.nan_to_num(left), np.nan_to_num(right), atol=1e-9, equal_nan=True))


def correlations(raw, spec):
    """Correlation of the cross-sectional mean of the lagged feature with each live factor."""
    panel = pd.read_csv(os.path.join(ROOT, PANEL), index_col=0, parse_dates=True)
    factors = build_factors(panel)
    lagged = feature(raw, spec)
    summary = lagged.mean(axis=1)
    summary.index = summary.index.tz_localize(None)
    out = {}
    for column in COMPONENTS:
        joined = pd.concat(
            [summary.rename("g"), factors[column].rename("f")], axis=1).dropna()
        out[column] = None if len(joined) < 30 else round(float(joined["g"].corr(joined["f"])), 4)
    return out


def halves(spread):
    """First half against second half of the non-missing spread, not a searched cut."""
    part = spread.dropna()
    mid = len(part) // 2
    rows = {}
    for name, chunk in (("first_half", part.iloc[:mid]), ("second_half", part.iloc[mid:])):
        independent = chunk.iloc[::1]
        t_stat = None
        if len(independent) > 2 and independent.std() > 0:
            t_stat = float(independent.mean() / (independent.std() / np.sqrt(len(independent))))
        rows[name] = {
            "spread": None if independent.empty else float(independent.mean()),
            "n": int(len(independent)),
            "t": t_stat,
        }
    return rows


def main():
    names = names_from_cache()
    raw = load_columns(names)
    spans = spans_for(raw["close"].columns)
    close = raw["close"]
    scored = []
    for spec in CELLS:
        lagged = feature(raw, spec)
        net = close.shift(-spec["horizon"]) / close - 1 - COST
        spread = daily_spread(lagged, net, spans, spec)
        periods = {name: block(spread, start, end, spec["horizon"])
                   for name, start, end in PERIODS}
        train_spread = periods["train"]["spread_independent"]
        train_sign = 0 if train_spread is None else (train_spread > 0) - (train_spread < 0)
        word, reason = verdict(periods, train_sign)
        held = lookahead(raw, spec)
        corr = correlations(raw, spec)
        largest = max(
            ((abs(value), column) for column, value in corr.items() if value is not None),
            default=(None, None))
        split = halves(spread)
        same_sign = (
            split["first_half"]["spread"] is not None
            and split["second_half"]["spread"] is not None
            and (split["first_half"]["spread"] > 0) == (split["second_half"]["spread"] > 0)
        )
        payload = {
            "item": spec["item"],
            "cell": spec["cell"],
            "candidate": spec["name"],
            "transform": spec["transform"],
            "horizon": spec["horizon"],
            "prereg_commit": PREREG,
            "prereg": "research/generated.md items 25 to 27",
            "names": int(close.shape[1]),
            "panel_end": str(close.index.max().date()),
            "target_note": spec["target_note"],
            "cost_note": (
                "thin-tier round trip of 30 bps, no funding carry, matching "
                "scripts/sweep_xs.py net_returns; the panel has no USD open interest"
            ),
            "train_sign": train_sign,
            "verdict": word,
            "reason": reason,
            "lookahead_holds": held,
            "correlation_with_live_factors": corr,
            "largest_abs_correlation": None if largest[0] is None else round(largest[0], 4),
            "largest_abs_correlation_with": largest[1],
            "halves": split,
            "same_sign_both_halves": same_sign,
            "periods": periods,
        }
        path = write_result(spec["name"], payload, inputs=[CACHE, PANEL_XS, PANEL, "research/generated.md"])
        scored.append(payload)
        print(path)
        print(json.dumps({
            "item": spec["item"], "verdict": word, "lookahead": held,
            "largest_corr": payload["largest_abs_correlation"],
            "periods": periods}))
    summary_path = write_result("regime-weekly-research", {
        "job": "regime-weekly-research",
        "prereg_commit": PREREG,
        "candidates": scored,
        "added": [],
        "panel_end": scored[-1]["panel_end"],
        "names": scored[-1]["names"],
    }, inputs=[CACHE, PANEL_XS, PANEL])
    print(summary_path)


if __name__ == "__main__":
    main()
