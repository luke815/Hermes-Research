"""Inventory of the point-in-time panel: name counts, date range, coverage.

Usage: python3 scripts/panel_xs_inventory.py
"""

import json
import os
from datetime import datetime, timezone

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs")
SERIES = ["close", "volume_usd", "funding_rate", "oi_usd"]


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    universe = pd.read_csv(os.path.join(ROOT, "data", "universe.csv"))
    coverage = {s: {} for s in SERIES}
    names_with = {s: 0 for s in SERIES}
    first, last = None, None
    for _, name in universe.iterrows():
        path = os.path.join(PANEL, f"{name['exchange']}_{name['symbol']}.csv")
        frame = pd.read_csv(path)
        if frame.empty:
            continue
        frame["year"] = frame["date"].str[:4]
        if first is None or frame["date"].min() < first:
            first = frame["date"].min()
        if last is None or frame["date"].max() > last:
            last = frame["date"].max()
        for series in SERIES:
            if series not in frame.columns:
                continue
            present = frame[frame[series].notna()]
            if present.empty:
                continue
            names_with[series] += 1
            for year, count in present.groupby("year").size().items():
                coverage[series][year] = coverage[series].get(year, 0) + int(count)
    inventory = {
        "as_of": today,
        "names": int(len(universe)),
        "listed": int((universe["delisted"] == 0).sum()),
        "delisted": int(universe["delisted"].sum()),
        "first_date": first,
        "last_date": last,
        "names_with_series": names_with,
        "rows_per_series_per_year": coverage,
        "note": ("The stores hold the delisted names only. Listed names have a file "
                 "but no rows, because their history has not been pulled."),
    }
    out = os.path.join(ROOT, "results", f"{today}_panel_xs_inventory.json")
    json.dump(inventory, open(out, "w"), indent=1)
    print(json.dumps(inventory, indent=1))


if __name__ == "__main__":
    main()
