"""Score the pre-registered G24 cell on the full panel, not the train cache.

Cell roc_12|xs_rank|above|95|rel_1|pit_cross_section|none|daily, as written
in research/generated.md item 24, commit 1152280. The indicator cache the
sweep wrote ends at the train cutoff, so scoring from it reports empty
held-out periods. This reads the close from the panel files for the same
234 names, computes the 12-bar rate of change the library uses, ranks it
across names, and lags it one bar. The target is rel_1. Subtracting BTC's
return from every name on the same date cancels inside a same-day rank, so
the rel_1 spread equals the ret_1 spread; the payload records that and
scores ret_1. The net is the sweep's own: the thin-tier round trip, with no
funding carry, because the panel has no USD open interest for the live
names. The pass rule is the pre-registered one. A price change after day t
must leave the signal at t unchanged, and that check is in the results file.
This does not pull and it does not write a confirmation row.
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
from ta.momentum import ROCIndicator  # noqa: E402

from regime_tester.confirm import (  # noqa: E402
    TEST_START, TRAIN_END, VALIDATION_END, VALIDATION_START,
)
from regime_tester.pit import apply_listing_mask  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402
from regime_tester.vectorized import transform_matrix  # noqa: E402

CELL = "roc_12|xs_rank|above|95|rel_1|pit_cross_section|none|daily"
CACHE = "data/panel_xs_cache/indicators_91ee884150ff50aa_4953200eab4e_v3.csv"
PANEL = "data/panel_xs_laevitas"
HORIZON = 1
THRESHOLD = 95.0
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


def names_from_cache():
    """The 234 names the train row was scored on, taken from the cache header."""
    wide = pd.read_csv(os.path.join(ROOT, CACHE), header=[0, 1], index_col=0, nrows=0)
    return list(wide["roc_12"].columns)


def load_close(names):
    frames = {}
    for name in names:
        path = os.path.join(ROOT, PANEL, name + ".csv")
        frame = pd.read_csv(path, usecols=["date", "close"])
        frame["date"] = pd.to_datetime(frame["date"], utc=True)
        frames[name] = frame.set_index("date")["close"].astype(float).sort_index()
    return pd.DataFrame(frames).sort_index()


def roc_matrix(close):
    """The library's 12-bar rate of change, early bars left empty."""
    columns = {}
    for name in close.columns:
        series = close[name].dropna()
        columns[name] = pd.Series(
            ROCIndicator(series, 12).roc().to_numpy(), index=series.index)
    return pd.DataFrame(columns).reindex(close.index)


def spans_for(columns):
    from scripts.sweep_xs import panel_spans
    return panel_spans(columns)


def daily_spread(cut, net, spans):
    """Flagged minus the rest, at the 95th percentile of the cross-sectional rank."""
    masked = apply_listing_mask(cut.reindex(columns=net.columns), spans)
    values = masked.to_numpy(dtype=float)
    returns = net.to_numpy(dtype=float)
    out = np.full(len(values), np.nan)
    for i in range(len(values)):
        both = ~np.isnan(values[i]) & ~np.isnan(returns[i])
        if both.sum() < MIN_NAMES:
            continue
        present = values[i][both]
        flagged = present >= THRESHOLD
        if flagged.sum() < 2 or (~flagged).sum() < 2:
            continue
        got = returns[i][both]
        out[i] = got[flagged].mean() - got[~flagged].mean()
    return pd.Series(out, index=cut.index)


def block(spread, start, end):
    part = spread[(spread.index >= start) & (spread.index <= end)].dropna()
    if part.empty:
        return {"spread_independent": None, "n_independent": 0, "t": None,
                "n_overlap": 0}
    independent = part.iloc[::HORIZON]
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


def lookahead(close):
    """Perturb every price after the midpoint and check the signal there is unchanged."""
    t = len(close) // 2
    base = roc_matrix(close.to_frame("x"))["x"]
    perturbed = close.copy()
    perturbed.iloc[t + 1:] = perturbed.iloc[t + 1:] + 1.0
    other = roc_matrix(perturbed.to_frame("x"))["x"]
    left = base.iloc[:t + 1].to_numpy(dtype=float)
    right = other.iloc[:t + 1].to_numpy(dtype=float)
    return bool(np.allclose(np.nan_to_num(left), np.nan_to_num(right), atol=1e-9))


def main():
    names = names_from_cache()
    close = load_close(names)
    ranked = transform_matrix(roc_matrix(close), "xs_rank").shift(1)
    net = close.shift(-HORIZON) / close - 1 - COST
    spread = daily_spread(ranked, net, spans_for(close.columns))
    periods = {name: block(spread, start, end) for name, start, end in PERIODS}
    train_spread = periods["train"]["spread_independent"]
    train_sign = 0 if train_spread is None else (train_spread > 0) - (train_spread < 0)
    word, reason = verdict(periods, train_sign)
    one = close.columns[0]
    held = lookahead(close[one].dropna())
    payload = {
        "item": "G24",
        "cell": CELL,
        "prereg_commit": "1152280a274b79ead9d75fbc7c6d377e031ddd85",
        "prereg": "research/generated.md item 24",
        "names": int(close.shape[1]),
        "panel_end": str(close.index.max().date()),
        "horizon": HORIZON,
        "target_note": (
            "rel_1 equals ret_1 inside a same-day rank: subtracting BTC's "
            "return from every name on one date cancels in the spread"
        ),
        "cost_note": (
            "thin-tier round trip of 30 bps, no funding carry, matching "
            "scripts/sweep_xs.py net_returns; the panel has no USD open interest"
        ),
        "train_sign": train_sign,
        "verdict": word,
        "reason": reason,
        "lookahead_holds": held,
        "lookahead_name": one,
        "periods": periods,
    }
    path = write_result("g24_roc_12", payload, inputs=[
        CACHE, PANEL, "research/generated.md"])
    print(path)
    print(json.dumps({
        "verdict": word, "names": int(close.shape[1]), "lookahead": held,
        "panel_end": payload["panel_end"], "periods": periods}))


if __name__ == "__main__":
    main()
