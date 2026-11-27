"""Fetch one Laevitas window and save it. Prints only a count, never the key.

Usage: python3 fetch_window.py <currency> <start> <end> <outfile>
"""

import json
import os
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from http_get import atomic_text, fetch  # noqa: E402
from rate_budget import BudgetStop  # noqa: E402

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
    target = OUT / outfile
    if target.exists() and target.stat().st_size > 2:
        print(f"exists, skipping {outfile}")
        return
    params = urllib.parse.urlencode({
        "series": "futures_annualized_basis", "currency": currency, "days": 90,
        "resolution": "1d", "start": start, "end": end, "limit": 200, "page": 1,
    })
    url = f"https://apiv2.laevitas.ch/api/v1/derivatives/funding-history?{params}"
    secret = key()
    try:
        payload = json.loads(fetch(url, timeout=90, headers={"apikey": secret, "X-API-Key": secret}))
    except BudgetStop as exc:
        print(f"stopped: {exc}; {outfile} not written")
        return
    items = payload.get("data", payload).get("items", [])
    atomic_text(target, json.dumps(items))
    print(f"saved {len(items)} -> {outfile}")


if __name__ == "__main__":
    main()
