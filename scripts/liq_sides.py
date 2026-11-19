"""Long and short liquidation share for BTC, by month, from the Coinalyze file.

If the long share is stable while the total jumps, the jump is coverage, not a
change in which side is counted.
"""

import json
from datetime import datetime, timezone

d = json.load(open("data/raw/coinalyze_liquidation-history.json"))
by_month = {}
for series in d["data"]:
    if not series["symbol"].startswith("BTC"):
        continue
    for bar in series["history"]:
        day = datetime.fromtimestamp(bar["t"], timezone.utc).strftime("%Y-%m")
        if day < "2025-10":
            continue
        by_month.setdefault(day, []).append((bar["l"], bar["s"]))
for month in sorted(by_month):
    rows = by_month[month]
    total = sum(l + s for l, s in rows)
    longs = sum(l for l, _ in rows)
    print(month, "days", len(rows), "long share", round(longs / total, 3) if total else None)
