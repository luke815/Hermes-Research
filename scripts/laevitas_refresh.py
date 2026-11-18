"""Refill the last 14 days of the market-level Laevitas series.

The scheduler runs this. A day already saved is left alone, and a day that
is missing, including one deleted after the last run, is requested again and
written back. No model action is involved.

The routes are the v1 history endpoints from data/laevitas/INVENTORY.md.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rate_budget  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "data", "raw")
BASE = "https://api.laevitas.ch"
WINDOW = 14

# stem, route. The stem is what regime_tester.derivatives globs on.
SERIES = (
    ("rr_btc", "/historical/options/type/risk_reversal/deribit/BTC/25d"),
    ("rr_eth", "/historical/options/type/risk_reversal/deribit/ETH/25d"),
    ("skew_btc", "/historical/options/type/skew/deribit/BTC/25d"),
    ("skew_eth", "/historical/options/type/skew/deribit/ETH/25d"),
    ("atm_iv_btc", "/historical/options/atm_iv/deribit/BTC"),
    ("atm_iv_eth", "/historical/options/atm_iv/deribit/ETH"),
    ("dvol_btc", "/historical/options/dvol/deribit/BTC"),
    ("dvol_eth", "/historical/options/dvol/deribit/ETH"),
    ("iv_rv_btc", "/historical/options/iv_rv/deribit/BTC"),
    ("iv_rv_eth", "/historical/options/iv_rv/deribit/ETH"),
)


def key():
    for line in open("/opt/data/.env"):
        if line.startswith("LAEVITAS_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("LAEVITAS_API_KEY missing")


def days(today, window=WINDOW):
    """The last `window` closed days. Today has no daily bar yet."""
    end = datetime.strptime(today, "%Y-%m-%d").date() - timedelta(days=1)
    return [(end - timedelta(days=offset)).isoformat() for offset in range(window - 1, -1, -1)]


def _day(stamp):
    stamp = int(stamp)
    if stamp > 10_000_000_000:
        stamp //= 1000
    return datetime.fromtimestamp(stamp, timezone.utc).date().isoformat()


def saved_days(stem):
    """Dates already on disk for one series, across every daily file."""
    found = set()
    if not os.path.isdir(STORE):
        return found
    for filename in os.listdir(STORE):
        if not filename.startswith(stem + "_") or not filename.endswith(".json"):
            continue
        try:
            payload = json.load(open(os.path.join(STORE, filename)))
        except (OSError, json.JSONDecodeError):
            continue
        rows = payload if isinstance(payload, list) else payload.get("items", [])
        found.update(_day(row["date"]) for row in rows if isinstance(row, dict) and row.get("date"))
    return found


def missing(stem, today, window=WINDOW):
    return [day for day in days(today, window) if day not in saved_days(stem)]


def fetch(route, start, end, getter=None):
    url = f"{BASE}{route}?start={start}&end={end}&granularity=1d&page=1&limit=100"
    getter = getter or rate_budget.get_json
    body = getter(url, {"apikey": key(), "User-Agent": "Mozilla/5.0"}, timeout=60, allowance="laevitas")
    data = body.get("data", body) if isinstance(body, dict) else {}
    return data.get("items", [])


def refill(today, getter=None):
    """Write back every missing day in the window. Returns what was filled."""
    os.makedirs(STORE, exist_ok=True)
    filled = {}
    for stem, route in SERIES:
        gaps = missing(stem, today)
        if not gaps:
            filled[stem] = []
            continue
        rows = fetch(route, gaps[0], gaps[-1], getter)
        wanted = set(gaps)
        got = [row for row in rows if _day(row.get("date", 0)) in wanted]
        if got:
            path = os.path.join(STORE, f"{stem}_gap.json")
            have = []
            if os.path.exists(path):
                try:
                    have = json.load(open(path))
                except json.JSONDecodeError:
                    have = []
            seen = {row.get("date") for row in have}
            have.extend(row for row in got if row.get("date") not in seen)
            tmp = path + ".tmp"
            json.dump(have, open(tmp, "w"))
            os.replace(tmp, path)
        filled[stem] = sorted({_day(row["date"]) for row in got})
    return filled


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    result = refill(today)
    out = os.path.join(ROOT, "results", f"{today}_laevitas_refresh.json")
    json.dump({"date": today, "filled": result}, open(out, "w"), indent=1)
    print(json.dumps({"date": today, "gaps": {k: v for k, v in result.items() if v}}))


if __name__ == "__main__":
    main()
