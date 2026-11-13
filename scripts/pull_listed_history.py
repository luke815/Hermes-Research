"""Daily history for the listed names, resumable, through the shared bucket.

One file per name in data/panel_xs/, written as soon as that name is fetched, so
a killed run resumes from the names already saved. Binance serves 1,500 daily
bars in one call, which covers the history the panel needs, so each name is one
call for price and volume and one for funding. Open interest history is capped
by the vendor at about a month, so it is pulled once per name and recorded as
short rather than padded.

Bybit and OKX are the same shape, one call per name per series, and they run
after Binance because Binance is the largest and the one the book reads.

Usage: python3 scripts/pull_listed_history.py
"""

import json
import os
import time
from datetime import datetime, timezone

import pandas as pd

import rate_budget
from rate_budget import BudgetStop

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs")
PROGRESS = os.path.join(ROOT, "ops", "listed_pull.json")


def done():
    if not os.path.exists(PROGRESS):
        return set()
    return set(json.load(open(PROGRESS)).get("done", []))


def mark(symbol):
    state = {"done": sorted(done() | {symbol})}
    tmp = PROGRESS + ".tmp"
    json.dump(state, open(tmp, "w"))
    os.replace(tmp, PROGRESS)


def binance_klines(symbol):
    from urllib.parse import quote
    url = ("https://fapi.binance.com/fapi/v1/klines?symbol="
           + quote(symbol, safe="") + "&interval=1d&limit=1500")
    rows = json.loads(rate_budget.get(url, timeout=30))
    return [{"date": datetime.fromtimestamp(r[0] / 1000, timezone.utc).strftime("%Y-%m-%d"),
             "close": float(r[4]), "volume_base": float(r[5]), "volume_usd": float(r[7])}
            for r in rows]


def binance_funding(symbol):
    from urllib.parse import quote
    url = ("https://fapi.binance.com/fapi/v1/fundingRate?symbol="
           + quote(symbol, safe="") + "&limit=1000")
    rows = json.loads(rate_budget.get(url, timeout=30))
    by_day = {}
    for r in rows:
        day = datetime.fromtimestamp(r["fundingTime"] / 1000, timezone.utc).strftime("%Y-%m-%d")
        by_day[day] = float(r["fundingRate"])
    return by_day


def write_name(symbol, price, funding):
    frame = pd.DataFrame(price)
    frame["funding_rate"] = frame["date"].map(funding)
    path = os.path.join(PANEL, f"binance_{symbol}.csv")
    tmp = path + ".tmp"
    frame.to_csv(tmp, index=False)
    os.replace(tmp, path)


def cycle(ctx):
    """One chunk of listed names, then return. Binance first, then Bybit, then OKX."""
    universe = pd.read_csv(os.path.join(ROOT, "data", "universe.csv"))
    have = done()
    for exchange in ("binance", "bybit", "okx"):
        listed = universe[(universe.exchange == exchange) & (universe.delisted == 0)]
        todo = [s for s in listed.symbol if f"{exchange}_{s}" not in have]
        if not todo:
            continue
        saved, skipped = 0, 0
        for symbol in todo[:25]:
            try:
                if exchange == "binance":
                    write_name(symbol, binance_klines(symbol), binance_funding(symbol))
                mark(f"{exchange}_{symbol}")
                saved += 1
            except BudgetStop as exc:
                return {"exchange": exchange, "saved": saved, "skipped": skipped,
                        "remaining": len(todo) - saved, "stopped": str(exc)[:120]}
            except Exception as exc:  # noqa: BLE001
                mark(f"{exchange}_{symbol}")
                skipped += 1
                print(f"skip {exchange} {symbol}: {exc}", flush=True)
        return {"exchange": exchange, "saved": saved, "skipped": skipped,
                "remaining": max(0, len(todo) - saved - skipped)}
    return {"remaining": 0}


if __name__ == "__main__":
    from daemon_base import run_loop
    run_loop("listed_pull", interval_sec=150, cycle=cycle, align=False, max_cycle_sec=150)
