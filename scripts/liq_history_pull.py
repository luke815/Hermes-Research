"""BTC and ETH aggregated liquidations from 2021-11-20, one page per cycle.

The instrument puller holds liquidations behind unfinished option histories,
so this walks the retained history itself. A page is saved before the next is
requested, and a killed run resumes from the pages already on disk. The daily
grid is a midnight sample, not a daily sum, so the file says so.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rate_budget  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "data", "laevitas", "liquidations_agg")
PROGRESS = os.path.join(ROOT, "ops", "liq_history.json")
BASE = "https://apiv2.laevitas.ch/api/v1/derivatives/liquidation-history"
CURRENCIES = ("BTC", "ETH")
START = datetime(2021, 11, 20, tzinfo=timezone.utc)
LIMIT = 1440


def key():
    for line in open("/opt/data/.env"):
        if line.startswith("LAEVITAS_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("LAEVITAS_API_KEY missing")


def windows(today):
    """Year-long windows. A multi-year request returns 503."""
    out = []
    start = START
    end_limit = datetime.strptime(today, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    while start <= end_limit:
        stop = min(start + timedelta(days=364), end_limit)
        out.append((start.strftime("%Y-%m-%d"), stop.strftime("%Y-%m-%d")))
        start = stop + timedelta(days=1)
    return out


def jobs(today):
    return [(currency, start, end) for currency in CURRENCIES for start, end in windows(today)]


def path_for(currency, start):
    return os.path.join(STORE, f"{currency}_{start[:4]}.json")


def load(path):
    if not os.path.exists(path):
        return None
    try:
        return json.load(open(path))
    except json.JSONDecodeError:
        return None


def pending_page(today):
    """The next unfetched page, or None when both currencies are saved."""
    for currency, start, end in jobs(today):
        body = load(path_for(currency, start)) or {"items": [], "pages": {}}
        fetched = {int(page) for page in body.get("pages", {})}
        page = 1
        while page in fetched:
            meta = body["pages"][str(page)]
            # A page saved below the request size is a partial write. Refetch it
            # rather than treating the window as finished.
            if meta.get("items", 0) < LIMIT and page < meta.get("total_pages", page):
                break
            if page >= meta.get("total_pages", page) or meta.get("items", 1) == 0:
                page = None
                break
            page += 1
        if page:
            return currency, start, end, page
    return None


def fetch_page(currency, start, end, page):
    url = (f"{BASE}?exchange=aggregated&currency={currency}&resolution=1d"
           f"&start={start}T00:00:00Z&end={end}T23:59:59Z&page={page}&limit={LIMIT}")
    return rate_budget.get_json(
        url, {"apikey": key(), "User-Agent": "Mozilla/5.0"},
        timeout=90, allowance="laevitas")


def save_page(currency, start, end, page, payload):
    """Append one page. A page already saved is not written twice."""
    os.makedirs(STORE, exist_ok=True)
    path = path_for(currency, start)
    body = load(path) or {
        "currency": currency, "start": start, "end": end,
        "resolution": "1d", "note": "midnight sample, not a daily sum",
        "items": [], "pages": {},
    }
    data = payload.get("data", payload) if isinstance(payload, dict) else {}
    items = data.get("items", [])
    have = {(row.get("date"), row.get("side")) for row in body["items"]}
    for row in items:
        if (row.get("date"), row.get("side")) not in have:
            body["items"].append(row)
    meta = data.get("meta", {})
    body["pages"][str(page)] = {
        "total": meta.get("total"), "items": meta.get("items", len(items)),
        "total_pages": meta.get("total_pages"),
    }
    body["end"] = end
    tmp = path + ".tmp"
    json.dump(body, open(tmp, "w"))
    os.replace(tmp, path)
    return body


def cycle(ctx):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    nxt = pending_page(today)
    if not nxt:
        return {"remaining": 0}
    currency, start, end, page = nxt
    payload = fetch_page(currency, start, end, page)
    body = save_page(currency, start, end, page, payload)
    left = pending_page(today)
    return {"currency": currency, "window": start, "page": page,
            "rows": len(body["items"]), "remaining": 1 if left else 0}


if __name__ == "__main__":
    from daemon_base import run_loop
    run_loop("liq_history", interval_sec=30, cycle=cycle, align=False, max_cycle_sec=120)
