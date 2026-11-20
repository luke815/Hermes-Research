"""Score the pre-registered C8 cascade rule.

The rule is research/generated.md item 19, committed before this script
existed. For each name in the Coinalyze liquidation file, liquidations are
the sum of the long and short fields. The 3-day sum at day t uses only bars
up to and including the prior bar, and the flag fires when that sum exceeds
the 95th percentile of its own trailing 90-day history, the window also
ending at the prior bar, with at least 30 days of history. Neighbours are
the 90th and the 99th percentile. A missing side leaves the day out.

The forward return is the close at t+h over the close at t, minus one, net
of the round trip and the funding carry. A missing carry leaves the net
missing. The spread is flagged minus unflagged, and the t-stat is taken on
every h-th bar.
"""

import json
import os
import subprocess
import sys

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.costs import apply_costs  # noqa: E402
from regime_tester.periods import assign_period  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
PREREG = "research/generated.md"
LIQ = os.path.join(RAW, "coinalyze_liquidation-history.json")
OHLCV = os.path.join(RAW, "coinalyze_ohlcv-history.json")
OI = os.path.join(RAW, "coinalyze_open-interest-history.json")
FUNDING = os.path.join(RAW, "coinalyze_funding-rate-history.json")
WINDOW = 90
MIN_HISTORY = 30
SUM_DAYS = 3
PRIMARY = 0.95
NEIGHBOURS = (0.90, 0.99)
HORIZONS = (1, 3, 5)
BAR = 2.0
MIN_INDEP = 30


def prereg_commit():
    out = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", PREREG],
        cwd=ROOT, capture_output=True, text=True, check=True)
    return out.stdout.strip()


def load(path, fields):
    blob = json.loads(open(path).read())
    names = {symbol: asset for asset, symbol in blob["symbols"].items()}
    out = {}
    for entry in blob["data"]:
        frame = pd.DataFrame(entry["history"])
        index = pd.to_datetime(frame["t"], unit="s", utc=True).dt.normalize()
        taken = frame.loc[:, list(fields)].apply(pd.to_numeric, errors="coerce")
        taken.index = index
        out[names[entry["symbol"]]] = taken[~taken.index.duplicated(keep="last")].sort_index()
    return out


def cascade_flag(long_side, short_side, pct):
    """Flag from bars strictly before day t. A missing side leaves the day out."""
    both = long_side.notna() & short_side.notna()
    total = (long_side + short_side).where(both)
    trailing = total.shift(1).rolling(SUM_DAYS, min_periods=SUM_DAYS).sum()
    history = trailing.rolling(WINDOW, min_periods=MIN_HISTORY)
    bar = history.quantile(pct)
    ready = history.count() >= MIN_HISTORY
    return trailing.gt(bar) & ready


def indep_t(flagged, rest):
    """Unequal-variance t on the independent sample. Empty sides stay absent."""
    flagged = flagged.dropna()
    rest = rest.dropna()
    if len(flagged) < 2 or len(rest) < 2:
        return None
    gap = float(flagged.mean() - rest.mean())
    se = np.sqrt(flagged.var(ddof=1) / len(flagged) + rest.var(ddof=1) / len(rest))
    if not se or np.isnan(se):
        return None
    return float(gap / se)


def score_name(close, funding, oi, flag, horizon):
    """Net forward return and the lagged flag, aligned on the close's dates."""
    net = apply_costs(close, horizon, side=1, funding=funding, oi_usd=oi)["net"]
    return flag.reindex(close.index), net


def cell_stats(flag, net, horizon):
    """Flagged-minus-rest spread per period, with the independent t-stat."""
    frame = pd.DataFrame({"flag": flag, "net": net}).dropna()
    frame["period"] = assign_period(frame.index)
    frame = frame.dropna(subset=["period"])
    out = {}
    for period in ("train", "validation", "test"):
        part = frame[frame["period"] == period]
        flagged = part.loc[part["flag"], "net"]
        rest = part.loc[~part["flag"], "net"]
        stride = part.iloc[::horizon]
        flagged_i = stride.loc[stride["flag"], "net"]
        rest_i = stride.loc[~stride["flag"], "net"]
        out[period] = {
            "n_flagged": int(len(flagged)),
            "n_rest": int(len(rest)),
            "n_flagged_indep": int(len(flagged_i)),
            "spread": None if flagged.empty or rest.empty else float(flagged.mean() - rest.mean()),
            "flagged_mean": None if flagged.empty else float(flagged.mean()),
            "rest_mean": None if rest.empty else float(rest.mean()),
            "hit_rate": None if flagged.empty else float((flagged > 0).mean()),
            "base_rate": None if part.empty else float((part["net"] > 0).mean()),
            "t_indep": indep_t(flagged_i, rest_i),
        }
    return out


def year_split(flag, net, horizon):
    frame = pd.DataFrame({"flag": flag, "net": net}).dropna()
    out = {}
    for year, part in frame.groupby(frame.index.year):
        stride = part.iloc[::horizon]
        flagged = part.loc[part["flag"], "net"]
        rest = part.loc[~part["flag"], "net"]
        flagged_i = stride.loc[stride["flag"], "net"]
        rest_i = stride.loc[~stride["flag"], "net"]
        out[str(int(year))] = {
            "dates": int(len(part)),
            "dates_indep": int(len(stride)),
            "n_flagged_indep": int(len(flagged_i)),
            "spread": None if flagged.empty or rest.empty else float(flagged.mean() - rest.mean()),
            "t_indep": indep_t(flagged_i, rest_i),
        }
    return out


def pooled_day(rows, horizon):
    """One observation per date: the mean net of the names flagged that day, minus the rest."""
    frame = pd.concat(rows)
    frame = frame.dropna(subset=["flag", "net"])
    by_day = frame.groupby(frame.index).apply(
        lambda g: pd.Series({
            "flagged": g.loc[g["flag"], "net"].mean(),
            "rest": g.loc[~g["flag"], "net"].mean(),
            "n_flagged": int(g["flag"].sum()),
        }), include_groups=False)
    by_day["period"] = assign_period(by_day.index)
    out = {}
    for period in ("train", "validation", "test"):
        part = by_day[by_day["period"] == period].dropna(subset=["flagged", "rest"])
        stride = part.iloc[::horizon]
        out[period] = {
            "dates": int(len(part)),
            "dates_indep": int(len(stride)),
            "spread": None if part.empty else float((part["flagged"] - part["rest"]).mean()),
            "t_indep": indep_t(stride["flagged"] - stride["rest"], pd.Series(0.0, index=stride.index)),
            "flagged_names": int(part["n_flagged"].sum()) if not part.empty else 0,
        }
    return out


def sign_flip(stats):
    held = [stats[p]["spread"] for p in ("validation", "test")]
    if any(v is None for v in held):
        return None
    return held[0] > 0 and held[1] < 0


def verdict_of(btc_cells, pooled_primary):
    """Rejected when the held-out sign flips and no cell clears the bar.

    The review asks the reason to say the pooled 1-day validation t did not
    reach 2 and the test is a null, not a flip. That wording is used only
    when the numbers say it. Otherwise the reason states what the numbers do.
    """
    primary = next(c for c in btc_cells if c["pct"] == PRIMARY and c["horizon"] == 1)
    pooled = pooled_primary
    val_t = pooled["validation"]["t_indep"]
    test_t = pooled["test"]["t_indep"]
    test_spread = pooled["test"]["spread"]
    null_test = test_t is not None and abs(test_t) < BAR
    below = val_t is not None and abs(val_t) < BAR
    flips = []
    for cell in btc_cells:
        if cell["pct"] != PRIMARY:
            continue
        if sign_flip(cell["periods"]):
            flips.append(f"BTC {cell['horizon']}d")
    if sign_flip(pooled):
        flips.append("pooled 1d")
    if below and null_test:
        reason = (
            f"validation t {val_t:.2f} on {pooled['validation']['dates']} dates "
            f"did not reach 2, and the test is a null (t {test_t:.2f}), not a flip"
        )
        return "rejected", reason
    reason = (
        f"pooled 1d validation t {val_t}, test spread {test_spread}, test t {test_t}; "
        f"sign flips on {flips or 'none'}"
    )
    return "rejected" if flips else "insufficient", reason


def lookahead_holds(liquidations):
    """Perturbing every liquidation after day t leaves the flag at t unchanged."""
    btc = liquidations["BTC"]
    t = len(btc) // 2
    before = cascade_flag(btc["l"], btc["s"], PRIMARY)
    noisy = btc.copy()
    noisy.iloc[t + 1:, 0] = noisy.iloc[t + 1:, 0] + 1_000_000_000
    noisy.iloc[t + 1:, 1] = noisy.iloc[t + 1:, 1] + 1_000_000_000
    after = cascade_flag(noisy["l"], noisy["s"], PRIMARY)
    return bool(before.iloc[:t + 1].equals(after.iloc[:t + 1]))


def main():
    liquidations = load(LIQ, ("l", "s"))
    closes = load(OHLCV, ("c",))
    oi = load(OI, ("c",))
    funding = load(FUNDING, ("c",))
    passed = lookahead_holds(liquidations)
    cells = []
    per_name = {pct: [] for pct in (PRIMARY,) + NEIGHBOURS}
    for asset, liq in liquidations.items():
        close = closes[asset]["c"]
        fund = funding.get(asset, pd.DataFrame({"c": []}))["c"] if asset in funding else None
        book = oi.get(asset, pd.DataFrame({"c": []}))["c"] if asset in oi else None
        for pct in (PRIMARY,) + NEIGHBOURS:
            flag = cascade_flag(liq["l"], liq["s"], pct)
            for horizon in HORIZONS:
                aligned, net = score_name(close, fund, book, flag, horizon)
                stats = cell_stats(aligned, net, horizon)
                if asset == "BTC":
                    cells.append({
                        "asset": "BTC", "pct": pct, "horizon": horizon,
                        "periods": stats, "years": year_split(aligned, net, horizon),
                    })
                per_name[pct].append(pd.DataFrame({
                    "flag": aligned, "net": net, "asset": asset}))
    pooled = {}
    for pct, rows in per_name.items():
        for horizon in HORIZONS:
            pooled[(pct, horizon)] = pooled_day(rows, horizon)
    btc_primary = [c for c in cells if c["pct"] == PRIMARY]
    verdict, reason = verdict_of(btc_primary, pooled[(PRIMARY, 1)])
    payload = {
        "item": "C8",
        "prereg_commit": prereg_commit(),
        "prereg": PREREG,
        "names": len(liquidations),
        "lookahead_passed": passed,
        "definition": (
            "3-day sum of long plus short, lagged one bar, above its own "
            "trailing 90-day percentile, also lagged, min 30 days"
        ),
        "cells": cells,
        "pooled": [
            {"pct": pct, "horizon": horizon, "periods": stats}
            for (pct, horizon), stats in pooled.items()
        ],
        "primary": {"asset": "pooled", "pct": PRIMARY, "horizon": 1,
                    "periods": pooled[(PRIMARY, 1)]},
        "verdict": verdict,
        "verdict_reason": reason,
    }
    path = write_result("c8_cascade", payload, inputs=[
        "data/raw/coinalyze_liquidation-history.json",
        "data/raw/coinalyze_ohlcv-history.json",
        "data/raw/coinalyze_open-interest-history.json",
        "data/raw/coinalyze_funding-rate-history.json",
        PREREG,
    ])
    print(json.dumps({"path": path, "lookahead": passed, "verdict": verdict,
                      "reason": reason}))


if __name__ == "__main__":
    main()
