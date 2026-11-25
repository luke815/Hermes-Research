"""Build the point-in-time universe: first and last bar per perp.

Coinalyze serves delisted names by symbol, so the universe is every USDT perp
on Binance, Bybit and OKX that has history, not today's listings. Writes
data/universe.json incrementally so a timeout does not lose progress.
"""

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from http_get import fetch  # noqa: E402
from rate_budget import BudgetStop  # noqa: E402

ROOT = Path("/opt/data/workspace/regime-tester")
OUT = ROOT / "data" / "universe.json"
VENUES = {"A": "binance", "6": "bybit", "3": "okx"}


def key() -> str:
    for line in open("/opt/data/.env"):
        if line.startswith("COINALYZE_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("no key")


def get(url: str) -> list:
    try:
        return json.loads(fetch(url, timeout=120, headers={"api_key": key()}))
    except BudgetStop as exc:
        print(f"stopped: {exc}", flush=True)
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
        got = get("https://api.coinalyze.net/v1/ohlcv-history?" + params)
        if not got:
            print("pull stopped; resume will continue from the names saved", flush=True)
            break
        for series in got:
            hist = series.get("history", [])
            if hist:
                inventory.append({"symbol": series["symbol"], "first": hist[0]["t"],
                                  "last": hist[-1]["t"], "bars": len(hist)})
        tmp = OUT.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(inventory))
        tmp.replace(OUT)
    print(f"done: {len(inventory)} names with history", flush=True)


if __name__ == "__main__":
    main()
