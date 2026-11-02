"""Build the point-in-time universe: first and last bar per perp.

Coinalyze serves delisted names by symbol, so the universe is every USDT perp
on Binance, Bybit and OKX that has history, not today's listings. Writes
data/universe.json incrementally so a timeout does not lose progress.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester")
OUT = ROOT / "data" / "universe.json"
VENUES = {"A": "binance", "6": "bybit", "3": "okx"}


def key() -> str:
    for line in open("/opt/data/.env"):
        if line.startswith("COINALYZE_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("no key")


def get(url: str) -> list:
    for _ in range(4):
        req = urllib.request.Request(url, headers={"api_key": key()})
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            if error.code == 429:
                time.sleep(float(error.headers.get("Retry-After", 5)) + 1)
                continue
            raise
    return []


def main() -> None:
    markets = get("https://api.coinalyze.net/v1/future-markets")
    perps = [m["symbol"] for m in markets
             if m.get("is_perpetual") and m.get("exchange") in VENUES and m.get("quote_asset") == "USDT"]
    done = {row["symbol"] for row in json.loads(OUT.read_text())} if OUT.exists() else set()
    inventory = json.loads(OUT.read_text()) if OUT.exists() else []
    remaining = [s for s in perps if s not in done]
    print(f"{len(perps)} perps, {len(done)} already saved, {len(remaining)} to pull", flush=True)

    for start in range(0, len(remaining), 20):
        batch = remaining[start:start + 20]
        params = urllib.parse.urlencode({"symbols": ",".join(batch), "interval": "daily",
                                          "from": 1577836800, "to": 1794000000})
        for series in get("https://api.coinalyze.net/v1/ohlcv-history?" + params):
            hist = series.get("history", [])
            if hist:
                inventory.append({"symbol": series["symbol"], "first": hist[0]["t"],
                                  "last": hist[-1]["t"], "bars": len(hist)})
        OUT.write_text(json.dumps(inventory))
        time.sleep(1.2)
    print(f"done: {len(inventory)} names with history", flush=True)


if __name__ == "__main__":
    main()
