"""Page Laevitas history into data/inbox. Key stays in config, never printed."""

import json
import os
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from http_get import atomic_text, fetch  # noqa: E402
from rate_budget import BudgetStop  # noqa: E402

INBOX = Path("/opt/data/workspace/regime-tester/data/inbox")
CONFIG = Path("/opt/data/config.yaml")
BASE = "https://apiv2.laevitas.ch"

START = "2024-10-01T00:00:00Z"
END = "2025-10-01T00:00:00Z"

# The daily pull is percent per 8h, the same scale the dashboard shows
# (0.01 is 1 bp). The hourly pull is a fraction, one hundredth of that.
# A daily median outside this band means the scale changed and the rows
# must not be saved as if they were the old one.
DAILY_MEDIAN_LOW = 0.001
DAILY_MEDIAN_HIGH = 0.05


def api_key() -> str:
    text = CONFIG.read_text()
    match = re.search(r'mcp_servers:\n  laevitas:.*?apikey:\s*"([^"]+)"', text, re.S)
    if not match:
        raise SystemExit("no laevitas key in config")
    return match.group(1)


def get(path: str, params: dict, key: str) -> dict:
    url = f"{BASE}{path}?{urllib.parse.urlencode(params)}"
    try:
        return json.loads(fetch(url, timeout=60, headers={"apikey": key, "X-API-Key": key}))
    except BudgetStop:
        raise


def daily_funding_median(values) -> float:
    """Median of a daily funding pull. Empty is not a median."""
    ordered = sorted(v for v in values if v is not None)
    if not ordered:
        raise ValueError("daily funding pull has no values")
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def assert_daily_funding_scale(values) -> float:
    """Refuse a daily funding pull whose median is not percent per 8h.

    The hourly pull sits near 0.00004, a hundredth of the daily one, so a
    pull saved on the wrong resolution lands far below the band.
    """
    median = daily_funding_median(values)
    if not DAILY_MEDIAN_LOW <= median <= DAILY_MEDIAN_HIGH:
        raise ValueError(
            f"daily funding median {median} is outside "
            f"{DAILY_MEDIAN_LOW}..{DAILY_MEDIAN_HIGH}")
    return median


def page(path: str, params: dict, key: str):
    rows, seen = [], 1
    while True:
        try:
            payload = get(path, {**params, "page": seen, "limit": 1440}, key)
        except BudgetStop as exc:
            print(f"  stopped at page {seen}: {exc}", flush=True)
            return None
        data = payload.get("data", payload)
        items = data.get("items", [])
        rows.extend(items)
        meta = data.get("meta", {})
        pages = meta.get("total_pages", 1)
        print(f"  {path} page {seen}/{pages} ({len(rows)} rows)", flush=True)
        if seen >= pages or not items:
            return rows
        seen += 1


def main() -> None:
    key = api_key()
    INBOX.mkdir(parents=True, exist_ok=True)

    jobs = []
    for token in ("BTC", "ETH"):
        pair = f"{token}USDT"
        jobs.append((f"price_{token.lower()}.json",
                     "/api/v1/spot/candle-history",
                     {"exchange": "binance", "instrument_name": pair, "resolution": "1h",
                      "start": START, "end": END}))
        jobs.append((f"funding_{token.lower()}.json",
                     "/api/v1/derivatives/funding-history",
                     {"series": "oi_weighted_funding", "currency": token, "resolution": "1h",
                      "start": START, "end": END}))
        jobs.append((f"realized_vol_{token.lower()}.json",
                     "/api/v1/derivatives/funding-history",
                     {"series": "realized_volatility", "currency": token, "resolution": "1h",
                      "start": START, "end": END}))
        for series in ("atm_iv", "skew"):
            jobs.append((f"{series}_{token.lower()}.json",
                         "/api/v1/options/volatility-history",
                         {"series": series, "exchange": "deribit", "currency": token,
                          "resolution": "1h", "start": START, "end": END}))

    for name, path, params in jobs:
        target = INBOX / name
        if target.exists() and target.stat().st_size > 2:
            print(f"{name}: already saved, skipping", flush=True)
            continue
        print(name, flush=True)
        rows = page(path, params, key)
        if rows is None:
            print("stopped; rerun resumes from the files already saved", flush=True)
            return
        if name.startswith("funding_") and params.get("resolution") == "1d":
            assert_daily_funding_scale(row.get("value") for row in rows)
        atomic_text(target, json.dumps({"data": {"items": rows}}))
        print(f"  wrote {len(rows)} rows", flush=True)


if __name__ == "__main__":
    main()
