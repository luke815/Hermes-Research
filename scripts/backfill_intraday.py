"""Refill the hourly store the relative-strength board reads.

The store at data/intraday stopped on 2026-11-05 when the Coinalyze hourly
pull was retired, and the board has read that stale file ever since. Binance's
public klines cover the same names without a key, so this walks the top-100
universe and appends the missing hours. A bar whose close time is still in the
future is the bar still forming, and it is dropped. A name Binance does not
list is counted and skipped.

One call per name, so a full pass is about five minutes inside the shared
budget. The scheduler runs it hourly; a second copy exits on the lock.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import intraday_store  # noqa: E402
import rate_budget  # noqa: E402
from rate_budget import BudgetStop  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOP = os.path.join(ROOT, "data", "universe_top100.json")
HOUR = 3600


def binance_symbol(base):
    return base + "USDT" if base.isascii() else None


def missing_hours(symbol, now):
    """Hours to request, from the last stored bar to the last closed hour."""
    bars = intraday_store.read(symbol)
    last = bars[-1]["t"] if bars else now - 200 * HOUR
    start = last + HOUR
    end = now - (now % HOUR)
    if start > end:
        return None
    return start, end


def fetch(base, start, end, now):
    url = ("https://fapi.binance.com/fapi/v1/klines?symbol=" + quote(base + "USDT", safe="")
           + f"&interval=1h&startTime={start * 1000}&endTime={end * 1000}&limit=200")
    try:
        raw = rate_budget.get(url, timeout=30, allowance="intraday", wait=False)
    except BudgetStop:
        raise
    except Exception as exc:  # noqa: BLE001 — a bad name is skipped, not fatal
        return [], str(exc)[:80]
    bars = []
    for row in json.loads(raw):
        # The close time is the end of the hour, so it sits in the future for the
        # whole hour the bar covers. The bar is closed once the next one opens.
        open_time = int(row[0]) // 1000
        if open_time + HOUR > now:
            continue
        bars.append({"t": open_time, "o": float(row[1]), "h": float(row[2]),
                      "l": float(row[3]), "c": float(row[4]), "v": float(row[5])})
    return bars, None


def backfill(now=None):
    now = int(now if now is not None else time.time())
    names = [r["symbol"] for r in json.load(open(TOP))["rows"]]
    filled, current, skipped, errors = [], [], [], []
    for symbol in names:
        base = symbol.split("USDT")[0]
        if binance_symbol(base) is None:
            skipped.append(base)
            continue
        window = missing_hours(symbol, now)
        if window is None:
            current.append(base)
            continue
        try:
            bars, err = fetch(base, window[0], window[1], now)
        except BudgetStop as exc:
            errors.append({"symbol": base, "error": str(exc)})
            break
        if err:
            errors.append({"symbol": base, "error": err})
            continue
        if bars:
            intraday_store.append(symbol, bars)
            filled.append({"symbol": base, "bars": len(bars)})
    last = max((intraday_store.read(s)[-1]["t"] for s in names
                if intraday_store.read(s)), default=None)
    return {
        "as_of": datetime.fromtimestamp(last, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if last else None,
        "names": len(names), "filled": len(filled), "already_current": len(current),
        "skipped": skipped, "errors": errors, "bars_added": sum(f["bars"] for f in filled),
    }


def main():
    result = backfill()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = os.path.join(ROOT, "results", f"{today}_intraday_backfill.json")
    tmp = path + ".tmp"
    json.dump(result, open(tmp, "w"), indent=1)
    os.replace(tmp, path)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
