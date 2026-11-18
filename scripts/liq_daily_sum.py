"""Sum retained liquidation events into one USD total per UTC day.

The daily file in data/laevitas/liquidations_agg is a midnight sample of the
vendor's observation grid, and the vendor says that grid is not a daily sum.
This script reads the retained event feed instead, one day per cycle, and
writes long and short separately plus their total. The event feed's earliest
observed bar is 2025-09-26, so the walk starts there; earlier days have no
events to sum. A day with no events is absent, not written as zero. The
midnight-sample file is not touched.
"""

import json
import os
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rate_budget

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "data", "laevitas", "liquidations_sum")
PROGRESS = os.path.join(ROOT, "ops", "liq_daily_sum.json")
SAMPLE = os.path.join(ROOT, "data", "laevitas", "liquidations_agg")
BASE = "https://apiv2.laevitas.ch/api/v1/perpetuals/liquidations"
CURRENCIES = ("BTC", "ETH")
EXCHANGES = ("binance", "bybit", "okx", "hyperliquid", "kraken", "lighter", "nado", "deribit")
START = datetime(2025, 9, 26, tzinfo=timezone.utc)
LIMIT = 1000


def key():
    for line in open("/opt/data/.env"):
        if line.startswith("LAEVITAS_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("LAEVITAS_API_KEY missing")


def day_list(today):
    """Closed days only. Today's events are still arriving, so today is not summed."""
    end = datetime.strptime(today, "%Y-%m-%d").replace(tzinfo=timezone.utc) - timedelta(days=1)
    out = []
    day = START
    while day <= end:
        out.append(day.strftime("%Y-%m-%d"))
        day += timedelta(days=1)
    return out


def load(path):
    if not os.path.exists(path):
        return None
    try:
        return json.load(open(path))
    except json.JSONDecodeError:
        return None


def path_for(currency, day):
    return os.path.join(STORE, currency, f"{day[:4]}.json")


def done_days(currency):
    """Days already summed, read from the files rather than a progress mark.

    A walked day with no events is recorded under empty, and counts as done
    so it is not fetched again. It is not a zero sum.
    """
    done = set()
    folder = os.path.join(STORE, currency)
    if not os.path.isdir(folder):
        return done
    for name in os.listdir(folder):
        body = load(os.path.join(folder, name)) or {}
        done.update(body.get("days", {}))
        done.update(body.get("empty", []))
    return done


def pending(today):
    for currency in CURRENCIES:
        have = done_days(currency)
        for day in day_list(today):
            if day not in have:
                return currency, day
    return None


def rows_of(payload):
    """REST returns the rows under data as a list. A wrapped items list is accepted too."""
    if not isinstance(payload, dict):
        return [], {}
    data = payload.get("data", [])
    meta = payload.get("meta") or {}
    if isinstance(data, list):
        return data, meta
    return data.get("items", []), (data.get("meta") or meta)


def fetch_day(currency, day):
    """Every event of one closed day, across the venues that serve the feed."""
    start = f"{day}T00:00:00Z"
    end = (datetime.strptime(day, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
    rows = []
    pages = 0
    for exchange in EXCHANGES:
        cursor = None
        while True:
            query = {"exchange": exchange, "currency": currency, "start": start,
                     "end": end, "limit": LIMIT, "sort": "timestamp", "sort_dir": "ASC",
                     "detail": "full"}
            if cursor:
                query["cursor"] = cursor
            url = f"{BASE}?{urllib.parse.urlencode(query)}"
            payload = rate_budget.get_json(
                url, {"apikey": key(), "User-Agent": "Mozilla/5.0"},
                timeout=90, allowance="laevitas")
            items, meta = rows_of(payload)
            rows.extend(items)
            pages += 1
            cursor = meta.get("next_cursor")
            if not cursor or not items:
                break
    return rows, pages


def sum_events(rows):
    """Long and short separately, plus the total. No events means no day."""
    if not rows:
        return None
    out = {"long": 0.0, "short": 0.0, "events": 0}
    for row in rows:
        side = row.get("position_side")
        if side not in ("long", "short"):
            continue
        amount = row.get("amount_usd")
        if amount is None:
            continue
        out[side] += float(amount)
        out["events"] += 1
    if not out["events"]:
        return None
    out["total"] = out["long"] + out["short"]
    return out


def save_day(currency, day, summary, pages):
    os.makedirs(os.path.join(STORE, currency), exist_ok=True)
    path = path_for(currency, day)
    body = load(path) or {"currency": currency, "note": "daily sum of retained liquidation events",
                          "days": {}}
    entry = dict(summary)
    entry["pages"] = pages
    body["days"][day] = entry
    tmp = path + ".tmp"
    json.dump(body, open(tmp, "w"))
    os.replace(tmp, path)
    return path


def record_empty(currency, day):
    """A walked day with no events. Recorded so it is not fetched again, not summed as zero."""
    path = path_for(currency, day)
    body = load(path) or {"currency": currency, "days": {}}
    body.setdefault("empty", [])
    if day not in body["empty"]:
        body["empty"].append(day)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(body, open(path + ".tmp", "w"))
    os.replace(path + ".tmp", path)
    return path


def write_status(today):
    """The results file, written from the sums on disk, not from a typed payload."""
    from regime_tester.results_io import write_result
    payload = {"item": "L8", "store": "data/laevitas/liquidations_sum",
               "sample_store": "data/laevitas/liquidations_agg",
               "note": "The daily files in the sample store stay a midnight sample. "
                       "This file is the sum of retained events."}
    for currency in CURRENCIES:
        days = done_days(currency)
        payload[currency] = {"days_summed": len(days),
                             "first": min(days) if days else None,
                             "last": max(days) if days else None}
    payload["remaining"] = 0 if pending(today) is None else 1
    return write_result("l8_sum", payload, inputs=["data/laevitas/liquidations_sum"])


def cycle(ctx):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    nxt = pending(today)
    if not nxt:
        return {"remaining": 0}
    currency, day = nxt
    rows, pages = fetch_day(currency, day)
    summary = sum_events(rows)
    if summary:
        save_day(currency, day, summary, pages)
    else:
        record_empty(currency, day)
    left = pending(today)
    return {"currency": currency, "day": day, "events": 0 if not summary else summary["events"],
            "remaining": 1 if left else 0}


if __name__ == "__main__":
    from daemon_base import run_loop
    run_loop("liq_daily_sum", interval_sec=20, cycle=cycle, align=False, max_cycle_sec=300)
