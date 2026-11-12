"""Cycle position. Candidate top and bottom days for BTC and the pooled universe.

Uses the amended targets: a 20-day 30 percent drop for a top, a 20-day 30
percent rally with no more than a 7 percent giveback for a bottom. Episodes are
counted once per date, so a day on which many names fire counts as one.

Usage: python3 scripts/cycle.py
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from regime_tester.episodes import base_rates, bottom_event, top_event
from regime_tester.periods import assign_period

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs")
DATA = os.path.join(ROOT, "dashboard", "data.json")


def closes():
    out = {}
    for name in sorted(os.listdir(PANEL)):
        frame = pd.read_csv(os.path.join(PANEL, name))
        if "close" not in frame.columns or frame["close"].notna().sum() < 60:
            continue
        frame = frame.dropna(subset=["close"])
        index = pd.to_datetime(frame["date"], utc=True)
        out[name.replace(".csv", "")] = pd.Series(frame["close"].to_numpy(float), index=index)
    return out


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    names = closes()
    btc = names.get("binance_BTCUSDT")
    if btc is None or len(btc) < 60:
        print("no btc history")
        return
    high_60 = btc.rolling(60, min_periods=60).max()
    low_60 = btc.rolling(60, min_periods=60).min()
    dist_high = btc.iloc[-1] / high_60.iloc[-1] - 1
    dist_low = btc.iloc[-1] / low_60.iloc[-1] - 1
    # A candidate day is within 5 percent of the 60-day extreme, and only a
    # name with 60 days of history can be one. The event that follows is a 20
    # percent move within 30 days, which is what the episode count measures.
    btc_top = top_event(btc, 30, 0.20)
    btc_bottom = bottom_event(btc, 30, 0.20, 0.07)
    frames = []
    for series in names.values():
        if len(series) < 60:
            continue
        high = series.rolling(60, min_periods=60).max()
        low = series.rolling(60, min_periods=60).min()
        frames.append(pd.DataFrame({
            "top": top_event(series, 30, 0.20),
            "bottom": bottom_event(series, 30, 0.20, 0.07),
            "at_high": series >= high * 0.95,
            "at_low": series <= low * 1.05,
        }))
    stacked = pd.concat(frames)
    by_date_top = stacked.groupby(stacked.index)["top"].any()
    by_date_bottom = stacked.groupby(stacked.index)["bottom"].any()
    top_rates = base_rates(by_date_top, assign_period(by_date_top.index))
    bottom_rates = base_rates(by_date_bottom, assign_period(by_date_bottom.index))
    last = stacked.index.max()
    today_rows = stacked[stacked.index == last]
    cycle = {
        "as_of": str(last.date()),
        "btc": {
            "candidate_top": bool(dist_high >= -0.05),
            "candidate_bottom": bool(dist_low <= 0.05),
            "dist_60d_high": round(float(dist_high) * 100, 1),
            "dist_60d_low": round(float(dist_low) * 100, 1),
        },
        "universe": {
            "share_at_60d_high": round(float(today_rows["at_high"].mean()), 4),
            "share_at_60d_low": round(float(today_rows["at_low"].mean()), 4),
            "n_top_episodes": top_rates["all"]["episodes"],
            "n_bottom_episodes": bottom_rates["all"]["episodes"],
        },
        "note": "Amended targets, 20-day 30 percent. Episodes counted once per date.",
    }
    data = json.load(open(DATA))
    data["cycle"] = cycle
    tmp = DATA + ".tmp"
    json.dump(data, open(tmp, "w"))
    os.replace(tmp, DATA)
    print(f"cycle as_of {cycle['as_of']} btc_top {cycle['btc']['candidate_top']} "
          f"btc_bottom {cycle['btc']['candidate_bottom']} "
          f"episodes {cycle['universe']['n_top_episodes']}/{cycle['universe']['n_bottom_episodes']}")


if __name__ == "__main__":
    main()
