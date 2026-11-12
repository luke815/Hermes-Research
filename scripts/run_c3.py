"""C3: TD Sequential setups and countdowns as events.

Pre-registered in research/log.md on 2026-11-10 before this script existed.
Reads the retained Coinalyze file. Does not pull and does not write the panel.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from regime_tester.cycle_score import (
    HORIZON,
    LABELS,
    NEIGHBOURS,
    PRIMARY,
    ROOT,
    clean,
    evaluate,
    event_label,
    holds,
    load_funding,
    load_pooled,
    verdict_for,
    year_caveat,
)
from regime_tester.indicators import td_sequential

ASSETS = ("BTC", "ETH", "SOL")
SEED = 63


def weekly_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Weeks ending Sunday, built only from days that have already closed."""
    weekly = frame.resample("W-SUN").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
    return pd.DataFrame(weekly)


def completion(count: pd.Series, level: int) -> pd.Series:
    """1 on the bar a count completes, lagged one bar so the signal follows the close."""
    done = count.eq(level) | count.eq(-level)
    return done.shift(1).astype(float)


def run() -> dict:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ohlcv = _names(load_pooled())
    funding = load_funding()
    last = max(frame.index.max() for frame in ohlcv.values())
    rows = []
    base = {}
    for asset in ASSETS:
        frame = ohlcv[asset]
        close = frame["c"].rename("close")
        setup, countdown = td_sequential(close, frame["h"], frame["l"])
        weekly = weekly_frame(frame)
        w_setup, w_countdown = td_sequential(weekly["c"], weekly["h"], weekly["l"])
        signals = {
            "td_setup_sell": completion(setup, 9).where(setup.shift(1).eq(9), 0.0),
            "td_setup_buy": completion(setup, 9).where(setup.shift(1).eq(-9), 0.0),
            "td_countdown_sell": completion(countdown, 13).where(countdown.shift(1).eq(13), 0.0),
            "td_countdown_buy": completion(countdown, 13).where(countdown.shift(1).eq(-13), 0.0),
        }
        weekly_signals = {
            "td_setup_sell_weekly": completion(w_setup, 9).where(w_setup.shift(1).eq(9), 0.0),
            "td_setup_buy_weekly": completion(w_setup, 9).where(w_setup.shift(1).eq(-9), 0.0),
            "td_countdown_sell_weekly": completion(w_countdown, 13).where(w_countdown.shift(1).eq(13), 0.0),
            "td_countdown_buy_weekly": completion(w_countdown, 13).where(w_countdown.shift(1).eq(-13), 0.0),
        }
        for spec in LABELS:
            label = event_label(close, spec)
            base.setdefault(spec["name"], {})[asset] = year_caveat(label)
            if not spec["primary"]:
                continue
            side = spec["side"]
            chosen = {k: v for k, v in signals.items() if (side == "top") == k.endswith("sell")}
            for name, signal in chosen.items():
                rank = signal.reindex(close.index).fillna(0.0)
                primary = evaluate(name, side, rank, 1.0, label, close,
                                   funding.get(asset), spec["h"], SEED)
                primary["asset"] = asset
                primary["timeframe"] = "daily"
                primary["neighbours_hold"] = None
                primary["verdict"] = verdict_for(primary, True)
                rows.append(primary)
            for name, signal in weekly_signals.items():
                if (side == "top") != name.split("_weekly")[0].endswith("sell"):
                    continue
                daily = signal.reindex(close.index, method="ffill").fillna(0.0)
                primary = evaluate(name, side, daily, 1.0, label, close,
                                   funding.get(asset), spec["h"], SEED)
                primary["asset"] = asset
                primary["timeframe"] = "weekly"
                primary["neighbours_hold"] = None
                primary["verdict"] = verdict_for(primary, True)
                rows.append(primary)
    return {
        "today": stamp,
        "panel_end": last.strftime("%Y-%m-%d"),
        "candidate": "c3_td_sequential",
        "label": "amended T(30, 20) and B(30, 20, 7) on candidate days",
        "horizon_days": HORIZON,
        "base_rates": base,
        "rows": rows,
        "note": "Completions are events, so the cut is 1 and the neighbour check does not apply.",
    }



def _names(ohlcv):
    """Map the short asset names the scripts use onto the panel's filenames."""
    aliases = {"BTC": "binance_BTCUSDT", "ETH": "binance_ETHUSDT", "SOL": "binance_SOLUSDT"}
    return {aliases.get(name, name): frame for name, frame in ohlcv.items()} | {
        short: ohlcv[full] for short, full in aliases.items() if full in ohlcv}

def main() -> None:
    result = clean(run())
    stamp = result["today"]
    path = ROOT / "results" / f"{stamp}_c3_td_sequential.json"
    path.write_text(json.dumps(result))
    print(f"wrote {path} rows={len(result['rows'])}")


if __name__ == "__main__":
    main()
