"""Append missing Coinalyze daily bars. Key stays in the env file, never printed."""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAW = Path("/opt/data/workspace/regime-tester/data/raw")
ENV = Path("/opt/data/.env")
BASE = "https://api.coinalyze.net/v1"

ENDPOINTS = {
    "coinalyze_ohlcv-history.json": "ohlcv-history",
    "coinalyze_funding-rate-history.json": "funding-rate-history",
    "coinalyze_open-interest-history.json": "open-interest-history",
    "coinalyze_liquidation-history.json": "liquidation-history",
    "coinalyze_long-short-ratio-history.json": "long-short-ratio-history",
}
USD = {
    "open-interest-history": "true",
    "liquidation-history": "true",
}


def load_key() -> str:
    for line in ENV.read_text().splitlines():
        if line.startswith("COINALYZE_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("missing key")


def get(path: str, params: dict, key: str):
    url = f"{BASE}/{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"api_key": key})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < 5:
                wait = float(exc.headers.get("Retry-After", "2") or 2) + 0.3
                print(f"429, sleeping {wait:.1f}s", flush=True)
                time.sleep(wait)
                continue
            body = exc.read()[:200]
            print(f"http {exc.code} {path} {body!r}", flush=True)
            raise
    raise SystemExit("retries exhausted")


def main() -> None:
    key = load_key()
    now = int(time.time())
    # daily bars are stamped at 00:00 UTC of the completed day; stop at yesterday
    today = now - (now % 86400)
    end = today - 86400

    for filename, endpoint in ENDPOINTS.items():
        path = RAW / filename
        payload = json.loads(path.read_text())
        symbols = [s["symbol"] for s in payload["data"]]
        last = max(s["history"][-1]["t"] for s in payload["data"] if s["history"])
        start = last + 86400
        if start > end:
            print(f"{filename}: already current through {last}", flush=True)
            continue
        params = {
            "symbols": ",".join(symbols),
            "interval": "daily",
            "from": start,
            "to": end,
        }
        if endpoint in USD:
            params["convert_to_usd"] = USD[endpoint]
        print(f"{endpoint}: {start} -> {end} ({len(symbols)} symbols)", flush=True)
        fresh = get(endpoint, params, key)
        by_symbol = {row["symbol"]: row.get("history", []) for row in fresh}
        added = 0
        for series in payload["data"]:
            rows = [r for r in by_symbol.get(series["symbol"], []) if r["t"] > last]
            # drop an in-progress bar if the vendor stamped today
            rows = [r for r in rows if r["t"] <= end]
            series["history"].extend(rows)
            added += len(rows)
        path.write_text(json.dumps(payload))
        newest = max(s["history"][-1]["t"] for s in payload["data"])
        print(f"  saved {added} bars, newest {newest}", flush=True)
        time.sleep(1.6)


if __name__ == "__main__":
    main()
