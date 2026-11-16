"""Laevitas v1 perpetual history, one instrument per cycle, resumable.

Reads the instrument list and pulls daily history for each perpetual that does
not yet have a file, through the laevitas rate bucket. A name is marked done
only when its file is written.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rate_budget

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "data", "laevitas", "perpetuals")
INSTRUMENTS = os.path.join(ROOT, "data", "laevitas", "instruments.json")


def key():
    for line in open("/opt/data/.env"):
        if line.startswith("LAEVITAS_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("LAEVITAS_API_KEY missing")


def complete(path, today):
    """Done when the file holds every page, or its last bar is current.

    Files written before pages_fetched existed are complete when they reach
    today. A file that stops early is the page cap, and is refetched.
    """
    if not os.path.exists(path):
        return False
    try:
        body = json.load(open(path))
    except json.JSONDecodeError:
        return False
    if body.get("error"):
        return True
    meta = body.get("meta") or {}
    pages = meta.get("total_pages") or 1
    if body.get("pages_fetched") == pages and len(body.get("items", [])) == meta.get("total", len(body.get("items", []))):
        return True
    dates = [i.get("date") for i in body.get("items", []) if i.get("date")]
    if not dates:
        return False
    last = datetime.fromtimestamp(max(dates) / 1000, timezone.utc).strftime("%Y-%m-%d")
    return last >= today


def pending():
    rows = json.load(open(INSTRUMENTS))
    perps = [r for r in rows if r["type"] == "perpetual"]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return [r for r in perps if not complete(
        os.path.join(STORE, f"{r['market']}_{r['instrument']}.json"), today)]


def pull(row, end):
    symbol = urllib.parse.quote(row["instrument"], safe="")
    pages = []
    meta = None
    page = 1
    # A name listed in 2021 is more than 2000 daily bars, so the page cap has
    # to clear that. Five pages stopped at 1000 bars and looked like a delisting.
    while page <= 20:
        url = (f"https://api.laevitas.ch/historical/derivs/perpetuals/{row['market']}/{symbol}"
               f"?start=2021-03-26&end={end}&granularity=1d&page={page}&limit=1000")
        req = urllib.request.Request(url, headers={"apikey": key(), "User-Agent": "Mozilla/5.0"})
        body = json.loads(urllib.request.urlopen(req, timeout=60).read())
        meta = body.get("meta", meta)
        pages.extend(body.get("items", []))
        total_pages = (meta or {}).get("total_pages", 1)
        if page >= total_pages:
            break
        page += 1
    return {"meta": meta, "items": pages, "pages_fetched": page}


def cycle(ctx):
    left = pending()
    if not left:
        return {"remaining": 0}
    row = left[0]
    os.makedirs(STORE, exist_ok=True)
    end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        body = pull(row, end)
    except urllib.error.HTTPError as exc:
        if exc.code in (400, 404):
            path = os.path.join(STORE, f"{row['market']}_{row['instrument']}.json")
            json.dump({"items": [], "error": exc.code}, open(path, "w"))
            return {"empty": 1, "code": exc.code, "remaining": len(left) - 1}
        print(f"skip {row['market']} {row['instrument']}: {exc}", flush=True)
        return {"skipped": 1, "remaining": len(left)}
    except Exception as exc:  # noqa: BLE001
        print(f"skip {row['market']} {row['instrument']}: {exc}", flush=True)
        return {"skipped": 1, "remaining": len(left)}
    path = os.path.join(STORE, f"{row['market']}_{row['instrument']}.json")
    json.dump(body, open(path, "w"))
    return {"market": row["market"], "instrument": row["instrument"],
            "rows": len(body.get("items", [])), "remaining": len(left) - 1}


if __name__ == "__main__":
    from daemon_base import run_loop
    run_loop("laevitas_pull", interval_sec=2, cycle=cycle, align=False)
