"""Fetch one Laevitas window and save it. Prints only a count, never the key.

Usage: python3 fetch_window.py <currency> <start> <end> <outfile>
"""

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

CONFIG = Path("/opt/data/config.yaml")
OUT = Path("/opt/data/workspace/regime-tester/data/raw")


def key() -> str:
    text = CONFIG.read_text()
    match = re.search(r'mcp_servers:\n  laevitas:.*?apikey:\s*"([^"]+)"', text, re.S)
    if not match:
        raise SystemExit("no key")
    return match.group(1)


def main() -> None:
    currency, start, end, outfile = sys.argv[1:5]
    params = urllib.parse.urlencode({
        "series": "futures_annualized_basis", "currency": currency, "days": 90,
        "resolution": "1d", "start": start, "end": end, "limit": 200, "page": 1,
    })
    url = f"https://apiv2.laevitas.ch/api/v1/derivatives/funding-history?{params}"
    req = urllib.request.Request(url, headers={"apikey": key(), "X-API-Key": key()})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                payload = json.loads(resp.read())
            break
        except urllib.error.HTTPError as exc:
            print(f"http {exc.code}")
            if attempt == 2:
                raise SystemExit(1)
            time.sleep(float(exc.headers.get("Retry-After", 5)) + 1)
    items = payload.get("data", payload).get("items", [])
    (OUT / outfile).write_text(json.dumps(items))
    print(f"saved {len(items)} -> {outfile}")


if __name__ == "__main__":
    main()
