"""Cycle position. Candidate top and bottom days for BTC and the pooled universe.

Event definitions, as coded below: a top is followed by a 20 percent drop
within 30 days; a bottom by a 20 percent rally within 30 days with no more
than a 7 percent giveback first. A candidate day sits within 5 percent of the
60-day extreme. Episodes are
counted once per date, so a day on which many names fire counts as one.

Usage: python3 scripts/cycle.py
"""

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd

from regime_tester.episodes import base_rates, bottom_event, top_event
from regime_tester.periods import assign_period
from dashboard_io import update_keys  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs")
KEY = os.path.join(ROOT, "dashboard", "keys", "cycle.json")


def closes():
    out = {}
    for name in sorted(os.listdir(PANEL)):
        frame = pd.read_csv(os.path.join(PANEL, name))
        if "close" not in frame.columns or frame["close"].notna().sum() < 60:
            continue
        frame = frame.dropna(subset=["close"])
        index = pd.to_datetime(frame["date"], utc=True)
        # Bybit and OKX files are written newest-first; rolling windows need oldest-first.
        series = pd.Series(frame["close"].to_numpy(float), index=index).sort_index()
        out[name.replace(".csv", "")] = series[~series.index.duplicated(keep="last")]
    return out


def base_rate(frame, candidate, event, horizon=30):
    """Share of candidate name-days whose event followed within the horizon.

    The last horizon days have no outcome yet and are left out, so a young
    candidate is not counted as a miss.
    """
    cutoff = frame.index.max() - pd.Timedelta(days=horizon)
    rows = frame[(frame.index <= cutoff) & frame[candidate].fillna(False).astype(bool)]
    hits = rows[event].dropna()
    return round(float(hits.astype(bool).mean()), 4) if len(hits) else None


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
            "base_top_30d": base_rate(stacked, "at_high", "top"),
            "base_bottom_30d": base_rate(stacked, "at_low", "bottom"),
        },
        "definition": {"candidate_band": 0.05, "lookback_days": 60, "move": 0.20,
                       "within_days": 30, "bottom_max_giveback": 0.07},
        "note": ("Top: a 20 percent drop within 30 days. Bottom: a 20 percent rally within 30 days "
                 "with at most a 7 percent giveback. Candidate: within 5 percent of the 60-day "
                 "extreme. Episodes counted once per date."),
    }
    btc_frame = pd.DataFrame({"top": btc_top, "bottom": btc_bottom,
                              "at_high": btc >= high_60 * 0.95, "at_low": btc <= low_60 * 1.05})
    cycle["btc"]["base_top_30d"] = base_rate(btc_frame, "at_high", "top")
    cycle["btc"]["base_bottom_30d"] = base_rate(btc_frame, "at_low", "bottom")
    update_keys(DATA, {"cycle": cycle})
    print(f"cycle as_of {cycle['as_of']} btc_top {cycle['btc']['candidate_top']} "
          f"btc_bottom {cycle['btc']['candidate_bottom']} "
          f"episodes {cycle['universe']['n_top_episodes']}/{cycle['universe']['n_bottom_episodes']}")


if __name__ == "__main__":
    main()
