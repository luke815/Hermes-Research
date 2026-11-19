"""BTC liquidation total from the Coinalyze file, by month, against the hosted series.

If both jump together the change is in the vendor file. If only the hosted
series jumps, the change is in our read.
"""

import json
from datetime import datetime, timezone

raw = json.load(open("data/raw/coinalyze_liquidation-history.json"))
by_month = {}
for series in raw["data"]:
    if series["symbol"].startswith("BTC"):
        for bar in series["history"]:
            day = datetime.fromtimestamp(bar["t"], timezone.utc).strftime("%Y-%m")
            by_month[day] = by_month.get(day, 0) + bar["l"] + bar["s"]
for month in sorted(by_month):
    if month >= "2025-06":
        print("source", month, round(by_month[month] / 1e6, 1), "million")
