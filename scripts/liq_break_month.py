"""Monthly median of liq_BTC over oi_BTC, to pin the break to a month."""

import json

d = json.load(open("dashboard/data.json"))
by_month = {}
for day, level, open_interest in zip(d["series"]["date"], d["series"]["liq_BTC"], d["series"]["oi_BTC"]):
    if level and open_interest and day >= "2025-06":
        by_month.setdefault(day[:7], []).append(level / open_interest)
for month in sorted(by_month):
    vals = sorted(by_month[month])
    print(month, round(vals[len(vals) // 2], 6))
