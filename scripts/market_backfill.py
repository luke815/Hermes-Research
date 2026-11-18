"""Market-level Laevitas backfill, one series per cycle.

L9 names the series the instrument puller never fetches: the put-call ratio,
the 25-delta butterfly, the open-interest-weighted basis curve, the
derivatives summary, and the 2019-2020 options history. Each is one route,
paged from its own first date, and a page is saved before the next is asked
for, so a killed run resumes from the pages already on disk.

A research run does not pull. This file is the daemon's cycle, and the
inventory is written from the files, never from a request.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rate_budget  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "data", "laevitas", "market")
BASE = "https://api.laevitas.ch"
LIMIT = 1000

# name, route, first date. The first dates come from the v1 inventory probe.
SERIES = (
    ("oi_pc_ratio", "BTC", "/historical/options/oi_pc_ratio/deribit/BTC", "2020-09-25"),
    ("oi_pc_ratio", "ETH", "/historical/options/oi_pc_ratio/deribit/ETH", "2020-09-25"),
    ("butterfly_25d", "BTC", "/historical/options/type/butterfly/deribit/BTC/25d", "2019-03-31"),
    ("butterfly_25d", "ETH", "/historical/options/type/butterfly/deribit/ETH/25d", "2019-03-31"),
    ("oi_weighted_basis", "BTC", "/historical/futures/oi_weighted_basis/BTC", "2021-03-26"),
    ("oi_weighted_basis", "ETH", "/historical/futures/oi_weighted_basis/ETH", "2021-03-26"),
    ("derivs_summary", "BTC", "/historical/derivs/summary/BTC", "2021-03-26"),
    ("derivs_summary", "ETH", "/historical/derivs/summary/ETH", "2021-03-26"),
    ("atm_iv", "BTC", "/historical/options/atm_iv/deribit/BTC", "2019-03-31"),
    ("atm_iv", "ETH", "/historical/options/atm_iv/deribit/ETH", "2019-03-31"),
    ("dvol", "BTC", "/historical/options/dvol/deribit/BTC", "2021-03-25"),
    ("dvol", "ETH", "/historical/options/dvol/deribit/ETH", "2021-03-25"),
    ("skew_25d", "BTC", "/historical/options/type/skew/deribit/BTC/25d", "2019-03-31"),
    ("skew_25d", "ETH", "/historical/options/type/skew/deribit/ETH/25d", "2019-03-31"),
    ("risk_reversal_25d", "BTC", "/historical/options/type/risk_reversal/deribit/BTC/25d", "2019-03-31"),
    ("risk_reversal_25d", "ETH", "/historical/options/type/risk_reversal/deribit/ETH/25d", "2019-03-31"),
    ("iv_rv", "BTC", "/historical/options/iv_rv/deribit/BTC", "2019-03-30"),
    ("iv_rv", "ETH", "/historical/options/iv_rv/deribit/ETH", "2019-03-30"),
)


def key():
    for line in open("/opt/data/.env"):
        if line.startswith("LAEVITAS_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("LAEVITAS_API_KEY missing")


def windows(start, today):
    """Year-long windows. A multi-year request returns 503."""
    out = []
    cursor = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_limit = datetime.strptime(today, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    while cursor <= end_limit:
        stop = min(cursor + timedelta(days=364), end_limit)
        out.append((cursor.strftime("%Y-%m-%d"), stop.strftime("%Y-%m-%d")))
        cursor = stop + timedelta(days=1)
    return out


def jobs(today):
    return [
        (name, currency, route, start, end)
        for name, currency, route, first in SERIES
        for start, end in windows(first, today)
    ]


def path_for(name, currency, start):
    return os.path.join(STORE, f"{name}_{currency}_{start[:4]}.json")


def load(path):
    if not os.path.exists(path):
        return None
    try:
        return json.load(open(path))
    except json.JSONDecodeError:
        return None


def window_done(body):
    """Done when every page up to the last one the vendor named is saved.

    A page saved with fewer rows than requested, before the last page, is a
    partial write and is fetched again. An empty first page is a window the
    vendor has nothing for, which is done rather than a loop.
    """
    pages = body.get("pages", {})
    if not pages:
        return False
    last = max(int(page) for page in pages)
    meta = pages[str(last)]
    total = meta.get("total_pages") or last
    if last < total:
        return False
    return all(
        str(page) in pages and pages[str(page)].get("items", 0) >= LIMIT
        for page in range(1, total)
    )


def pending_page(today):
    """The next unfetched page, or None when every series is saved."""
    for name, currency, route, start, end in jobs(today):
        body = load(path_for(name, currency, start)) or {"items": [], "pages": {}}
        if window_done(body):
            continue
        fetched = {int(page) for page in body.get("pages", {})}
        page = 1
        while page in fetched:
            page += 1
        return name, currency, route, start, end, page
    return None


def fetch_page(route, start, end, page, getter=None):
    url = f"{BASE}{route}?start={start}&end={end}&granularity=1d&page={page}&limit={LIMIT}"
    getter = getter or rate_budget.get_json
    return getter(url, {"apikey": key(), "User-Agent": "Mozilla/5.0"}, timeout=90, allowance="laevitas")


def save_page(name, currency, route, start, end, page, payload):
    """Append one page. A date already saved is not written twice."""
    os.makedirs(STORE, exist_ok=True)
    path = path_for(name, currency, start)
    body = load(path) or {
        "name": name, "currency": currency, "route": route,
        "start": start, "end": end, "granularity": "1d", "items": [], "pages": {},
    }
    data = payload.get("data", payload) if isinstance(payload, dict) else {}
    items = data.get("items", [])
    have = {row.get("date") for row in body["items"]}
    for row in items:
        if row.get("date") not in have:
            body["items"].append(row)
            have.add(row.get("date"))
    meta = data.get("meta", {})
    body["pages"][str(page)] = {
        "total": meta.get("total"), "items": meta.get("items", len(items)),
        "total_pages": meta.get("total_pages"),
        "error": payload.get("error") if isinstance(payload, dict) else None,
    }
    body["end"] = end
    tmp = path + ".tmp"
    json.dump(body, open(tmp, "w"))
    os.replace(tmp, path)
    return body


def _day(stamp):
    stamp = int(stamp)
    if stamp > 10_000_000_000:
        stamp //= 1000
    return datetime.fromtimestamp(stamp, timezone.utc).date().isoformat()


def coverage():
    """First date, last date and missing-day count per series, from the files."""
    found = {}
    if os.path.isdir(STORE):
        for filename in sorted(os.listdir(STORE)):
            if not filename.endswith(".json"):
                continue
            body = load(os.path.join(STORE, filename)) or {}
            label = f"{body.get('name')}_{body.get('currency')}"
            found.setdefault(label, set()).update(
                _day(row["date"]) for row in body.get("items", []) if row.get("date"))
    rows = []
    for name, currency, _route, first in SERIES:
        label = f"{name}_{currency}"
        days = found.get(label, set())
        if days:
            start, end = min(days), max(days)
            span = (datetime.strptime(end, "%Y-%m-%d") - datetime.strptime(start, "%Y-%m-%d")).days + 1
            missing = span - len(days)
        else:
            start = end = None
            missing = None
        rows.append({
            "series": label, "expected_first": first, "first": start, "last": end,
            "rows": len(days), "missing_days": missing,
        })
    return rows


def write_inventory(path):
    """One line per series. A series with no file says so rather than a date."""
    lines = ["# Market-level Laevitas series", "",
             "Written by scripts/market_backfill.py from data/laevitas/market. A missing day is a calendar day between the first and last saved date with no row.", ""]
    for row in coverage():
        if row["first"] is None:
            lines.append(f"- {row['series']}: no file yet, expected from {row['expected_first']}")
        else:
            lines.append(
                f"- {row['series']}: first {row['first']}, last {row['last']}, "
                f"{row['rows']} rows, {row['missing_days']} missing days")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    open(tmp, "w").write("\n".join(lines) + "\n")
    os.replace(tmp, path)
    return path


def cycle(ctx, getter=None):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    nxt = pending_page(today)
    if not nxt:
        write_inventory(os.path.join(ROOT, "data", "INVENTORY.md"))
        return {"remaining": 0}
    name, currency, route, start, end, page = nxt
    try:
        payload = fetch_page(route, start, end, page, getter)
    except Exception as exc:
        # A 500 on one window must not stop the walk. Record it as fetched
        # with nothing in it, so the next cycle takes a different window.
        payload = {"meta": {"total": 0, "items": 0, "total_pages": page}, "items": [],
                   "error": type(exc).__name__}
    body = save_page(name, currency, route, start, end, page, payload)
    left = pending_page(today)
    return {"series": f"{name}_{currency}", "window": start, "page": page,
            "rows": len(body["items"]), "error": body["pages"][str(page)].get("error"),
            "remaining": 1 if left else 0}


if __name__ == "__main__":
    from daemon_base import run_loop
    run_loop("market_backfill", interval_sec=30, cycle=cycle, align=False, max_cycle_sec=120)
