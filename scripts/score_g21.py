"""Score the pre-registered G21 cell on the full panel, not the train cache.

Cell bb_pct|xs_rank|below|20|ret_10|pit_cross_section|none|daily, as written
in research/generated.md item 21. The indicator cache the sweep wrote ends
at the train cutoff, so scoring from it reports empty held-out periods.
This reads the close from the panel files for the same 234 names, computes
the Bollinger percent band with the same window and the same fill the
library uses, ranks it across names, and lags it one bar. The net is
regime_tester.costs per name: the thin tier, funding carry divided by 100,
and a missing carry leaves that name missing. The pass rule is the
pre-registered one. A price change after day t must leave the signal at t
unchanged, and that check is in the results file. This does not pull and
it does not write a confirmation row.
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
from ta.volatility import BollingerBands  # noqa: E402

from regime_tester.confirm import (  # noqa: E402
    TEST_START, TRAIN_END, VALIDATION_END, VALIDATION_START, hac_t,
)
from regime_tester.costs import apply_costs  # noqa: E402
from regime_tester.cross_section import decile_spread  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402
from regime_tester.vectorized import transform_matrix  # noqa: E402

CELL = "bb_pct|xs_rank|below|20|ret_10|pit_cross_section|none|daily"
CACHE = "data/panel_xs_cache/indicators_91ee884150ff50aa_4953200eab4e_v3.csv"
PANEL = "data/panel_xs_laevitas"
HORIZON = 10
WINDOW = 20
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
    return list(wide["bb_pct"].columns)


def load_frames(names):
    frames = {}
    for name in names:
        path = os.path.join(ROOT, PANEL, name + ".csv")
        frame = pd.read_csv(path, usecols=lambda c: c in ("date", "close", "funding_rate"))
        frame["date"] = pd.to_datetime(frame["date"], utc=True)
        frames[name] = frame.set_index("date").sort_index()
    return frames


def bb_pct(close):
    """The library's percent band: a 20-day window, early bars filled with 0."""
    band = BollingerBands(close, WINDOW).bollinger_pband()
    return pd.Series(band, index=close.index)


def measure_matrix(frames):
    columns = {name: bb_pct(frame["close"].astype(float)) for name, frame in frames.items()}
    return pd.DataFrame(columns).sort_index()


def net_matrix(frames, index):
    columns = {}
    for name, frame in frames.items():
        aligned = frame.reindex(index)
        funding = aligned["funding_rate"] if "funding_rate" in aligned.columns else None
        columns[name] = apply_costs(
            aligned["close"], HORIZON, side=1, funding=funding)["net"]
    return pd.DataFrame(columns, index=index)


def daily_spreads(signal, net):
    rows = []
    for date in signal.index:
        rows.append({"date": date, "spread": decile_spread(signal.loc[date], net.loc[date])})
    return pd.DataFrame(rows)


def block(scored, start, end):
    part = scored[(scored["date"] >= start) & (scored["date"] <= end)]["spread"].dropna()
    if part.empty:
        return {"spread_independent": None, "n_independent": 0, "t": None, "n_overlap": 0}
    stats = hac_t(part.to_numpy(), HORIZON)
    return {
        "spread_independent": float(part.iloc[::HORIZON].mean()),
        "n_independent": int(len(part.iloc[::HORIZON])),
        "t": stats.get("t_newey_west", stats.get("hac_t")),
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
    base = bb_pct(close)
    perturbed = close.copy()
    perturbed.iloc[t + 1:] = perturbed.iloc[t + 1:] + 1.0
    other = bb_pct(perturbed)
    left = base.iloc[:t + 1].to_numpy(dtype=float)
    right = other.iloc[:t + 1].to_numpy(dtype=float)
    return bool(np.allclose(np.nan_to_num(left), np.nan_to_num(right), atol=1e-9))


def main():
    names = names_from_cache()
    frames = load_frames(names)
    measure = measure_matrix(frames)
    signal = transform_matrix(measure, "xs_rank").shift(1)
    net = net_matrix(frames, signal.index)
    scored = daily_spreads(signal, net)
    periods = {name: block(scored, start, end) for name, start, end in PERIODS}
    train_spread = periods["train"]["spread_independent"]
    train_sign = 0 if train_spread is None else (train_spread > 0) - (train_spread < 0)
    word, reason = verdict(periods, train_sign)
    one = next(iter(frames))
    held = lookahead(frames[one]["close"].astype(float).dropna())
    payload = {
        "item": "G21",
        "cell": CELL,
        "prereg": "research/generated.md item 21",
        "names": len(frames),
        "panel_end": str(scored["date"].max().date()),
        "horizon": HORIZON,
        "train_sign": train_sign,
        "verdict": word,
        "reason": reason,
        "lookahead_holds": held,
        "lookahead_name": one,
        "periods": periods,
    }
    path = write_result("g21_bb_pct", payload, inputs=[
        CACHE, PANEL, "research/generated.md"])
    print(path)
    print(json.dumps({
        "verdict": word, "names": len(frames), "lookahead": held,
        "panel_end": payload["panel_end"], "periods": periods}))


if __name__ == "__main__":
    main()
