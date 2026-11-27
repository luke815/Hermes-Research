"""Read the last non-empty oi_pc_ratio bar for BTC and ETH.

Q4 needs a bar after 2025-06. This script reads the saved files and writes the
finding through write_result. It does not pull.
"""

import glob
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKET = os.path.join(ROOT, "data", "laevitas", "market")


def _items(path):
    loaded = json.load(open(path))
    data = loaded.get("data", loaded) if isinstance(loaded, dict) else loaded
    if isinstance(data, dict):
        data = data.get("items", data.get("data", []))
    return data if isinstance(data, list) else []


def _date(row):
    for key in ("date", "t", "timestamp"):
        if key in row:
            return row[key]
    return None


def last_bar(asset):
    files = sorted(glob.glob(os.path.join(MARKET, f"oi_pc_ratio_{asset}_*.json")))
    latest = None
    nonempty = 0
    for path in files:
        rows = _items(path)
        if not rows:
            continue
        nonempty += 1
        for row in rows:
            value = _date(row)
            if value is None:
                continue
            stamp = int(value) / 1000 if int(value) > 10 ** 12 else int(value)
            day = datetime.fromtimestamp(stamp, timezone.utc).strftime("%Y-%m-%d")
            if latest is None or day > latest:
                latest = day
    return {"files": len(files), "nonempty": nonempty,
            "empty": len(files) - nonempty, "last_bar": latest}


def main():
    out = {"item": "Q4", "btc": last_bar("BTC"), "eth": last_bar("ETH"),
           "after_2025_06": False}
    out["after_2025_06"] = all(
        out[asset]["last_bar"] and out[asset]["last_bar"] > "2025-06-30"
        for asset in ("btc", "eth"))
    path = write_result("q4_oi_pc", out, inputs=["data/laevitas/market"])
    print(path)


if __name__ == "__main__":
    main()
