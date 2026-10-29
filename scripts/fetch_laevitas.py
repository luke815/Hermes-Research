"""Page Laevitas history into data/inbox. Key stays in config, never printed."""

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

INBOX = Path("/opt/data/workspace/regime-tester/data/inbox")
CONFIG = Path("/opt/data/config.yaml")
BASE = "https://apiv2.laevitas.ch"

START = "2024-10-01T00:00:00Z"
END = "2025-10-01T00:00:00Z"


def api_key() -> str:
    text = CONFIG.read_text()
    match = re.search(r'mcp_servers:\n  laevitas:.*?apikey:\s*"([^"]+)"', text, re.S)
    if not match:
        raise SystemExit("no laevitas key in config")
    return match.group(1)


def get(path: str, params: dict, key: str) -> dict:
    url = f"{BASE}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"apikey": key, "X-API-Key": key})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < 4:
                time.sleep(int(exc.headers.get("Retry-After", 5)) + 1)
                continue
            raise


def page(path: str, params: dict, key: str) -> list[dict]:
    rows, seen = [], 1
    while True:
        payload = get(path, {**params, "page": seen, "limit": 1440}, key)
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
        print(name, flush=True)
        rows = page(path, params, key)
        (INBOX / name).write_text(json.dumps({"data": {"items": rows}}))
        print(f"  wrote {len(rows)} rows", flush=True)


if __name__ == "__main__":
    main()
