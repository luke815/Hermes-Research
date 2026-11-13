"""Backfill high and low into panel_xs from Binance daily klines.

The panel was built with close only. The range measures need high and low, and
Binance klines carry both in the same response. One name per cycle, resumable,
writing the two columns into the existing file.
"""

import json
import os
import sys
from datetime import datetime, timezone
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
import rate_budget

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs")
PROGRESS = os.path.join(ROOT, "ops", "high_low_progress.json")


def pending():
    done = set(json.load(open(PROGRESS))) if os.path.exists(PROGRESS) else set()
    return [f for f in sorted(os.listdir(PANEL))
            if f.startswith("binance_") and f.endswith(".csv") and f not in done]


def backfill(name):
    symbol = name.replace("binance_", "").replace(".csv", "")
    url = ("https://fapi.binance.com/fapi/v1/klines?symbol=" + quote(symbol, safe="")
           + "&interval=1d&limit=1500")
    try:
        got = json.loads(rate_budget.get(url, timeout=30))
    except Exception as exc:  # noqa: BLE001
        print(f"skip {symbol}: {exc}", flush=True)
        return 0
    bars = {datetime.fromtimestamp(row[0] / 1000, timezone.utc).strftime("%Y-%m-%d"):
            (float(row[2]), float(row[3])) for row in got}
    path = os.path.join(PANEL, name)
    frame = pd.read_csv(path)
    frame["high"] = frame["date"].map(lambda d: bars.get(d, (None, None))[0])
    frame["low"] = frame["date"].map(lambda d: bars.get(d, (None, None))[1])
    frame.to_csv(path, index=False)
    return int(frame["high"].notna().sum())


def cycle(ctx):
    left = pending()
    if not left:
        return {"remaining": 0}
    name = left[0]
    filled = backfill(name)
    done = set(json.load(open(PROGRESS))) if os.path.exists(PROGRESS) else set()
    done.add(name)
    json.dump(sorted(done), open(PROGRESS, "w"))
    return {"name": name, "filled": filled, "remaining": len(left) - 1}


if __name__ == "__main__":
    from daemon_base import run_loop
    run_loop("high_low", interval_sec=2, cycle=cycle, align=False)
