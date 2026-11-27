"""Score the pre-registered Q6 cross-sectional momentum cell.

The rules are research/outside/PREREG_Q6.md, committed before this script
existed. The spread and the rank IC are reported side by side, and a
disagreement between them is a rejection.
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
from regime_tester.periods import PERIODS  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREREG = "research/outside/PREREG_Q6.md"
PANEL_XS = os.path.join(ROOT, "data", "panel_xs_laevitas")
LOOKBACK = 14
HORIZON = 5
COST_BPS = 15
LEGS = 4
N_BAR = 40
MIN_NAMES = 10


def prereg_commit():
    added = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=%H", "--", PREREG],
        cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    if len(added) != 1:
        raise SystemExit(f"pre-registration was added in {len(added)} commits")
    commit = added[0]
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
        check=True).stdout.strip()
    if head == commit:
        raise SystemExit("scoring in the same commit as the pre-registration")
    return commit


def load():
    """Closes and funding, one column per coin, rescales dropped."""
    closes = {}
    funding = {}
    dropped = 0
    for name in sorted(os.listdir(PANEL_XS)):
        if not name.endswith(".csv"):
            continue
        coin = name[:-4].split("_", 1)[1].split("USDT")[0].split("-")[0]
        if not coin or coin in closes:
            continue
        frame = pd.read_csv(os.path.join(PANEL_XS, name), usecols=[
            "date", "close", "funding_rate"])
        frame["date"] = pd.to_datetime(frame["date"], utc=True)
        frame = frame.drop_duplicates("date").set_index("date").sort_index()
        close = frame["close"].astype(float)
        move = close.pct_change()
        if ((move < -0.95) | (move > 5)).any():
            dropped += 1
            continue
        closes[coin] = close
        funding[coin] = frame["funding_rate"].astype(float)
    return (pd.DataFrame(closes).sort_index(), pd.DataFrame(funding).sort_index(),
            dropped)


def period_of(index):
    stamps = pd.to_datetime(index)
    dates = pd.Series([stamp.strftime("%Y-%m-%d") for stamp in stamps], index=index)
    names = pd.Series("", index=index)
    for name, start, end in PERIODS:
        mask = pd.Series(True, index=index)
        if start is not None:
            mask = mask & (dates >= start)
        if end is not None:
            mask = mask & (dates <= end)
        names[mask] = name
    return names


def main():
    commit = prereg_commit()
    closes, funding, dropped = load()
    signal = closes.pct_change(LOOKBACK).shift(1)
    forward = closes.shift(-HORIZON) / closes - 1
    carry = funding.rolling(HORIZON).sum().shift(-HORIZON + 1) / 100
    weekly = signal.index[signal.index.dayofweek == 0]
    rows = []
    for date in weekly:
        if date not in signal.index:
            continue
        ranked = signal.loc[date].dropna()
        if len(ranked) < MIN_NAMES * 2:
            continue
        future = forward.loc[date].reindex(ranked.index)
        held = carry.loc[date].reindex(ranked.index) if date in carry.index else None
        cut = max(MIN_NAMES, len(ranked) // 10)
        long = ranked.nlargest(cut).index
        short = ranked.nsmallest(cut).index
        if future[long].isna().any() or future[short].isna().any():
            continue
        if held is None or held[long].isna().any() or held[short].isna().any():
            continue
        gross = float(future[long].mean() - future[short].mean())
        net = gross - LEGS * COST_BPS / 10000 - float(held[long].mean() - held[short].mean())
        both = pd.concat([ranked.rename("signal"), future.rename("forward")], axis=1).dropna()
        ic = float(both["signal"].corr(both["forward"], method="spearman")) if len(both) >= 5 else None
        rows.append({"date": date.strftime("%Y-%m-%d"), "names": int(len(ranked)),
                     "gross": round(gross, 6), "net": round(net, 6), "ic": None if ic is None else round(ic, 6)})
    frame = pd.DataFrame(rows)
    frame["period"] = period_of(pd.to_datetime(frame["date"], utc=True)).to_numpy()
    periods = {}
    for name, _, _ in PERIODS:
        part = frame[frame["period"] == name]
        row = {"rebalances": int(len(part))}
        if len(part):
            row["net"] = round(float(part["net"].mean()), 6)
            row["gross"] = round(float(part["gross"].mean()), 6)
            row["ic"] = round(float(part["ic"].mean()), 6)
        periods[name] = row
    held = [periods[name] for name in ("validation", "test")]
    if any("net" not in row or "ic" not in row for row in held):
        verdict = "insufficient"
    elif periods["train"]["rebalances"] + periods["validation"]["rebalances"] < N_BAR:
        verdict = "insufficient"
    elif any(row["net"] * row["ic"] <= 0 for row in held):
        verdict = "rejected"
    elif (held[0]["net"] > 0) != (held[1]["net"] > 0):
        verdict = "rejected"
    else:
        verdict = "kept"
    payload = {
        "prereg_commit": commit,
        "names": int(closes.shape[1]),
        "dropped_rescales": dropped,
        "rebalances": int(len(frame)),
        "periods": periods,
        "verdict": verdict,
    }
    path = write_result("q6_xs_momentum", payload,
                        inputs=["data/panel_xs_laevitas", PREREG])
    print(json.dumps({"path": path, "verdict": verdict, "periods": periods}))


if __name__ == "__main__":
    main()
