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

# procmgr restarts from a clean environment, which does not have the user
# site on its path. The libraries live there, so the script adds them itself.
_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
import rate_budget

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs")
PROGRESS = os.path.join(ROOT, "ops", "high_low_progress.json")


# One kline call returns the newest 1500 daily bars. A panel that starts
# before that window needs the earlier pages, or high and low exist only on
# the last few days and a range measure still has nothing to score.
PAGE = 1500


def column_complete(path):
    """True when high and low are present on every row that has a close.

    A header with a handful of recent values is the one-page write. That
    file stays pending, so a progress mark cannot hide a short column.
    """
    frame = pd.read_csv(path)
    if "high" not in frame.columns or "low" not in frame.columns:
        return False
    if "close" not in frame.columns or frame.empty:
        return False
    have_close = frame["close"].notna()
    return bool(have_close.any()) and bool(
        frame.loc[have_close, "high"].notna().all()
        and frame.loc[have_close, "low"].notna().all())


def pending():
    done = set(json.load(open(PROGRESS))) if os.path.exists(PROGRESS) else set()
    waiting = []
    for name in sorted(os.listdir(PANEL)):
        if not (name.startswith("binance_") and name.endswith(".csv")):
            continue
        path = os.path.join(PANEL, name)
        if name in done and column_complete(path):
            continue
        waiting.append(name)
    return waiting


def klines(symbol, getter):
    """Every daily bar, walking back a page at a time from the newest window."""
    bars = {}
    end = None
    for _page in range(20):
        url = ("https://fapi.binance.com/fapi/v1/klines?symbol="
               + quote(symbol, safe="") + f"&interval=1d&limit={PAGE}")
        if end is not None:
            url += f"&endTime={end - 1}"
        got = json.loads(getter(url, timeout=30))
        if not isinstance(got, list) or not got:
            break
        for row in got:
            bars[datetime.fromtimestamp(row[0] / 1000, timezone.utc).strftime("%Y-%m-%d")] = (
                float(row[2]), float(row[3]))
        oldest = min(row[0] for row in got)
        if len(got) < PAGE or end == oldest:
            break
        end = oldest
    return bars


def backfill(name, getter=None):
    symbol = name.replace("binance_", "").replace(".csv", "")
    getter = getter or (lambda url, timeout=30: rate_budget.get(url, timeout=timeout))
    try:
        bars = klines(symbol, getter)
    except Exception as exc:  # noqa: BLE001
        print(f"skip {symbol}: {exc}", flush=True)
        return 0
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
    path = os.path.join(PANEL, name)
    if not column_complete(path):
        return {"name": name, "filled": filled, "incomplete": 1,
                "remaining": len(left)}
    done = set(json.load(open(PROGRESS))) if os.path.exists(PROGRESS) else set()
    done.add(name)
    json.dump(sorted(done), open(PROGRESS, "w"))
    return {"name": name, "filled": filled, "remaining": len(left) - 1}


if __name__ == "__main__":
    from daemon_base import run_loop
    run_loop("high_low", interval_sec=2, cycle=cycle, align=False)
