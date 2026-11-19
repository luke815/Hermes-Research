"""Find where liq_BTC jumps relative to oi_BTC, from the hosted series."""

import json

d = json.load(open("dashboard/data.json"))
dates = d["series"]["date"]
liq = d["series"]["liq_BTC"]
oi = d["series"]["oi_BTC"]
by_year = {}
for day, level, open_interest in zip(dates, liq, oi):
    if level and open_interest:
        by_year.setdefault(day[:4], []).append(level / open_interest)
for year in sorted(by_year):
    vals = sorted(by_year[year])
    print(year, "n", len(vals), "median", round(vals[len(vals) // 2], 6))
