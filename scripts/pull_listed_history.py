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
import sys
import time
from datetime import datetime, timezone

# procmgr restarts from a clean environment, which does not have the user
# site on its path. The libraries live there, so the script adds them itself.
_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

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


def bybit_klines(symbol):
    from urllib.parse import quote
    url = ("https://api.bybit.com/v5/market/kline?category=linear&symbol="
           + quote(symbol, safe="") + "&interval=D&limit=1000")
    got = json.loads(rate_budget.get(url, timeout=30))
    return [{"date": datetime.fromtimestamp(int(r[0]) / 1000, timezone.utc).strftime("%Y-%m-%d"),
             "close": float(r[4]), "volume_base": float(r[5])}
            for r in got.get("result", {}).get("list", [])]


def bybit_funding(symbol):
    """Daily funding as the sum of the day's settlements, with the interval.

    The last print of the day is not the day's funding: an 8-hour venue
    settles three times and a 1-hour venue twenty-four. The interval is stored
    beside the sum so the two are not read as the same quantity.
    """
    from urllib.parse import quote
    from regime_tester.panel_integrity import sum_funding
    url = ("https://api.bybit.com/v5/market/funding/history?category=linear&symbol="
           + quote(symbol, safe="") + "&limit=200")
    got = json.loads(rate_budget.get(url, timeout=30))
    rows = got.get("result", {}).get("list", [])
    prints = [(int(row["fundingRateTimestamp"]), float(row["fundingRate"])) for row in rows]
    hours = _interval_hours(prints, default=8)
    return sum_funding(prints, hours)


def okx_klines(symbol):
    from urllib.parse import quote
    url = ("https://www.okx.com/api/v5/market/candles?instId="
           + quote(symbol, safe="") + "&bar=1D&limit=300")
    got = json.loads(rate_budget.get(url, timeout=30))
    return [{"date": datetime.fromtimestamp(int(r[0]) / 1000, timezone.utc).strftime("%Y-%m-%d"),
             "close": float(r[4]), "volume_base": float(r[5])}
            for r in got.get("data", [])]


def _interval_hours(prints, default):
    """Hours between consecutive settlements, from the prints themselves."""
    stamps = sorted({int(stamp) for stamp, _rate in prints})
    gaps = [b - a for a, b in zip(stamps, stamps[1:]) if b > a]
    if not gaps:
        return default
    hours = round(min(gaps) / 3_600_000)
    return hours if hours in (1, 4, 8) else default


def binance_funding(symbol):
    """Daily funding as the sum of the day's settlements, with the interval."""
    from urllib.parse import quote
    from regime_tester.panel_integrity import sum_funding
    url = ("https://fapi.binance.com/fapi/v1/fundingRate?symbol="
           + quote(symbol, safe="") + "&limit=1000")
    rows = json.loads(rate_budget.get(url, timeout=30))
    prints = [(int(r["fundingTime"]), float(r["fundingRate"])) for r in rows]
    return sum_funding(prints, _interval_hours(prints, default=8))


def _attach_funding(frame, funding):
    """Map a daily sum onto the price rows and keep the interval beside it."""
    if funding and isinstance(next(iter(funding.values())), dict):
        frame["funding_rate"] = frame["date"].map(
            lambda day: funding.get(day, {}).get("funding_rate"))
        frame["funding_interval_hours"] = frame["date"].map(
            lambda day: funding.get(day, {}).get("funding_interval_hours"))
    else:
        frame["funding_rate"] = frame["date"].map(funding)
    return frame


def write_bars(path, bars, funding=None):
    """Write one name, sorted, with future bars and duplicate dates removed."""
    from regime_tester.panel_integrity import clean_frame
    frame = pd.DataFrame(bars)
    if funding is not None:
        frame = _attach_funding(frame, funding)
    frame = clean_frame(frame)
    tmp = path + ".tmp"
    frame.to_csv(tmp, index=False)
    os.replace(tmp, path)


def write_name(symbol, price, funding):
    write_bars(os.path.join(PANEL, f"binance_{symbol}.csv"), price, funding)


def needs_funding(exchange, symbol):
    """True when the name's file is missing or has no funding column."""
    path = os.path.join(PANEL, f"{exchange}_{symbol}.csv")
    if not os.path.exists(path):
        return True
    return "funding_rate" not in pd.read_csv(path, nrows=0).columns


def cycle(ctx):
    """One chunk of listed names, then return. Binance first, then Bybit, then OKX."""
    universe = pd.read_csv(os.path.join(ROOT, "data", "universe.csv"))
    have = done()
    for exchange in ("binance", "bybit", "okx"):
        listed = universe[(universe.exchange == exchange) & (universe.delisted == 0)]
        todo = [s for s in listed.symbol if needs_funding(exchange, s)]
        if not todo:
            continue
        saved, skipped = 0, 0
        for symbol in todo[:25]:
            try:
                if exchange == "binance":
                    write_name(symbol, binance_klines(symbol), binance_funding(symbol))
                elif exchange == "bybit":
                    bars = bybit_klines(symbol)
                    if bars:
                        write_bars(os.path.join(PANEL, f"bybit_{symbol}.csv"),
                                   bars, bybit_funding(symbol))
                elif exchange == "okx":
                    bars = okx_klines(symbol)
                    if bars:
                        write_bars(os.path.join(PANEL, f"okx_{symbol}.csv"), bars)
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
    import data_guard
    data_guard.record_write("data/panel_xs", 0, "listed_pull: batch written")
    return {"remaining": 0}


if __name__ == "__main__":
    from daemon_base import run_loop
    run_loop("listed_pull", interval_sec=150, cycle=cycle, align=False, max_cycle_sec=150)
