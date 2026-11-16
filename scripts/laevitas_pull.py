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


def pending():
    rows = json.load(open(INSTRUMENTS))
    perps = [r for r in rows if r["type"] == "perpetual"]
    return [r for r in perps if not os.path.exists(
        os.path.join(STORE, f"{r['market']}_{r['instrument']}.json"))]


def pull(row, end):
    symbol = urllib.parse.quote(row["instrument"], safe="")
    pages = []
    meta = None
    page = 1
    while page <= 5:
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
    return {"meta": meta, "items": pages}


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
