"""Append yesterday's bar to every live name in the point-in-time panel.

The daily refresh owns the daily panel. This owns panel_xs, and it runs after
the refresh so the two end on the same date. One call per batch of 20, through
the shared budget, resumable from the dates already written.

Usage: python3 scripts/append_panel_xs.py
"""

import json
import os
from datetime import datetime, timezone, timedelta
import sys
from urllib.parse import quote

# procmgr restarts from a clean environment, which does not have the user
# site on its path. The libraries live there, so the script adds them itself.
_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rate_budget

PANEL = os.path.join(ROOT, "data", "panel_xs")


def live_names():
    universe = pd.read_csv(os.path.join(ROOT, "data", "universe.csv"))
    listed = universe[(universe.exchange == "binance") & (universe.delisted == 0)]
    return list(listed.symbol)


def append_batch(symbols, day):
    start = int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp() * 1000)
    rows = {}
    for symbol in symbols:
        url = ("https://fapi.binance.com/fapi/v1/klines?symbol=" + quote(symbol, safe="")
               + f"&interval=1d&startTime={start}&limit=1")
        try:
            got = json.loads(rate_budget.get(url, timeout=30))
        except Exception as exc:  # noqa: BLE001
            print(f"skip {symbol}: {exc}", flush=True)
            continue
        if got:
            rows[symbol] = {"date": day, "close": float(got[0][4]),
                            "high": float(got[0][2]), "low": float(got[0][3]),
                            "volume_base": float(got[0][5]), "volume_usd": float(got[0][7])}
    return rows


def main():
    from regime_tester.panel_integrity import replace_last_row
    yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    names = live_names()
    written = 0
    for i in range(0, len(names), 20):
        batch = append_batch(names[i:i + 20], yesterday)
        for symbol, row in batch.items():
            path = os.path.join(PANEL, f"binance_{symbol}.csv")
            frame = pd.read_csv(path) if os.path.exists(path) and os.path.getsize(path) > 40 else pd.DataFrame()
            # A date already present is the partial print of a day that has
            # now closed. Replace that row rather than keeping it.
            frame = replace_last_row(frame, row)
            tmp = path + ".tmp"
            frame.to_csv(tmp, index=False)
            os.replace(tmp, path)
            written += 1
        print(f"batch {i // 20 + 1}: {written} appended", flush=True)
    print(f"appended {written} bars for {yesterday}")
    import data_guard
    data_guard.record_write("data/panel_xs", written, "append_panel_xs: yesterday's bar")


if __name__ == "__main__":
    main()
