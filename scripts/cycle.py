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
    if btc is None:
        print("no btc")
        return
    btc_top = top_event(btc, 20, 0.30)
    btc_bottom = bottom_event(btc, 20, 0.30, 0.07)
    high_60 = btc.rolling(60, min_periods=60).max()
    low_60 = btc.rolling(60, min_periods=60).min()
    frames = []
    for series in names.values():
        frames.append(pd.DataFrame({
            "top": top_event(series, 20, 0.30),
            "bottom": bottom_event(series, 20, 0.30, 0.07),
            "at_high": series >= series.rolling(60, min_periods=60).max(),
            "at_low": series <= series.rolling(60, min_periods=60).min(),
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
            "candidate_top": bool(btc_top.iloc[-1]) if pd.notna(btc_top.iloc[-1]) else False,
            "candidate_bottom": bool(btc_bottom.iloc[-1]) if pd.notna(btc_bottom.iloc[-1]) else False,
            "dist_60d_high": round(float(btc.iloc[-1] / high_60.iloc[-1] - 1) * 100, 1),
            "dist_60d_low": round(float(btc.iloc[-1] / low_60.iloc[-1] - 1) * 100, 1),
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
