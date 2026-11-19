"""Laevitas history for the delisted names, one name per cycle.

The catalogue puller walks instruments.json, which lists names still trading.
A delisted name is absent from it, so its history is never requested and the
point-in-time universe has no funding, open interest or basis for it. This
walks the span files instead: a name is dead when its last file is more than
14 days before today, which is the rule the span files were built with. A
name whose file is already saved is skipped, and a 400 or 404 is recorded
with the day so it is retried after 7 days rather than marked done forever.

A research run does not pull. This file is the daemon's cycle.
"""

import csv
import json
import os
import sys
import urllib.error
import urllib.parse
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rate_budget  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "data", "laevitas", "delisted")
BASE = "https://api.laevitas.ch/historical/derivs/perpetuals"
START = "2021-03-26"
RETRY_AFTER_DAYS = 7
DEAD_AFTER_DAYS = 14

# Span file, the venue the catalogue uses, and the instrument form it serves.
VENUES = (
    ("data/binance_span.csv", "BINANCE", lambda symbol: symbol),
    ("data/bybit_span.csv", "BYBIT", lambda symbol: symbol),
    ("data/okx_span.csv", "OKX", lambda symbol: f"{symbol}-USDT-SWAP"),
)


def key():
    for line in open("/opt/data/.env"):
        if line.startswith("LAEVITAS_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("LAEVITAS_API_KEY missing")


def dead_names(today):
    """Names whose last span file is more than 14 days before today."""
    cutoff = datetime.strptime(today, "%Y-%m-%d").date() - timedelta(days=DEAD_AFTER_DAYS)
    out = []
    for span, market, instrument_of in VENUES:
        for row in csv.DictReader(open(os.path.join(ROOT, span))):
            last = row.get("last")
            if not last or datetime.strptime(last, "%Y-%m-%d").date() >= cutoff:
                continue
            out.append({"market": market, "symbol": row["symbol"],
                        "instrument": instrument_of(row["symbol"]), "last": last})
    return out


def path_for(row):
    return os.path.join(STORE, f"{row['market']}_{row['instrument']}.json")


def done(path, today):
    """Saved, or a recorded 400 or 404 that is less than 7 days old."""
    if not os.path.exists(path):
        return False
    try:
        body = json.load(open(path))
    except json.JSONDecodeError:
        return False
    if body.get("error"):
        seen = body.get("error_on")
        if not seen:
            return False
        gap = (datetime.strptime(today, "%Y-%m-%d").date()
               - datetime.strptime(seen, "%Y-%m-%d").date()).days
        return gap < RETRY_AFTER_DAYS
    return bool(body.get("items"))


def pending(today):
    return [row for row in dead_names(today) if not done(path_for(row), today)]


def fetch(row, today, getter=None):
    """Every page of one name, from 2021-03-26 to today."""
    getter = getter or rate_budget.get_json
    symbol = urllib.parse.quote(row["instrument"], safe="")
    market = urllib.parse.quote(row["market"], safe="")
    page = 1
    items = []
    meta = None
    while page <= 20:
        url = (f"{BASE}/{market}/{symbol}?start={START}&end={today}"
               f"&granularity=1d&page={page}&limit=1000")
        body = getter(url, {"apikey": key(), "User-Agent": "Mozilla/5.0"},
                      timeout=90, allowance="laevitas")
        meta = body.get("meta", meta)
        items.extend(body.get("items", []))
        if page >= (meta or {}).get("total_pages", 1):
            break
        page += 1
    return {"meta": meta, "items": items, "pages_fetched": page,
            "market": row["market"], "instrument": row["instrument"]}


def cycle(ctx, getter=None):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    left = pending(today)
    if not left:
        return {"remaining": 0}
    row = left[0]
    os.makedirs(STORE, exist_ok=True)
    path = path_for(row)
    try:
        body = fetch(row, today, getter)
    except urllib.error.HTTPError as exc:
        if exc.code in (400, 404):
            json.dump({"items": [], "error": exc.code, "error_on": today}, open(path, "w"))
            return {"empty": 1, "code": exc.code, "remaining": len(left) - 1}
        print(f"skip {row['market']} {row['instrument']}: {exc}", flush=True)
        return {"skipped": 1, "remaining": len(left)}
    except Exception as exc:  # noqa: BLE001 — one bad name does not stop the walk
        print(f"skip {row['market']} {row['instrument']}: {exc}", flush=True)
        return {"skipped": 1, "remaining": len(left)}
    tmp = path + ".tmp"
    json.dump(body, open(tmp, "w"))
    os.replace(tmp, path)
    return {"market": row["market"], "instrument": row["instrument"],
            "rows": len(body["items"]), "remaining": len(left) - 1}


if __name__ == "__main__":
    from daemon_base import run_loop
    run_loop("delisted_pull", interval_sec=20, cycle=cycle, align=False)
