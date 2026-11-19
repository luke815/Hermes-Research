"""Merge the delisted-name history into the Laevitas panel.

The catalogue panel was built from instruments.json, which lists names still
trading, so a delisted name has no file in data/panel_xs_laevitas. The
delisted pull saved those histories under data/laevitas/delisted. This writes
a panel file for each saved name that has bars, in the same columns and the
same naming as build_universe_laevitas, into a new directory that also holds
a copy of the existing panel. A name already in the panel is left as it is.
A saved file with no bars is counted and skipped, not written as an empty
frame.

Usage: python3 scripts/merge_delisted.py
"""

import json
import os
import shutil

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "data", "laevitas", "delisted")
PANEL = os.path.join(ROOT, "data", "panel_xs_laevitas")
OUT = os.path.join(ROOT, "data", "panel_xs_laevitas_delisted")
COLUMNS = ["date", "close", "volume_usd", "volume_base", "funding_rate", "oi_usd",
           "basis", "long_short_ratio"]


def day(millis):
    from datetime import datetime, timezone
    return datetime.fromtimestamp(millis / 1000, timezone.utc).strftime("%Y-%m-%d")


def frame_of(body):
    """One row per day, or None when the saved file has no priced bars."""
    items = [i for i in body.get("items", []) if i.get("price") is not None]
    if not items:
        return None
    items.sort(key=lambda i: i["date"])
    frame = pd.DataFrame({
        "date": [day(i["date"]) for i in items],
        "close": [i.get("price") for i in items],
        "volume_usd": [i.get("volume") for i in items],
        "volume_base": [i.get("volume_coin") for i in items],
        "funding_rate": [i.get("funding") for i in items],
        "oi_usd": [i.get("open_interest") for i in items],
        "basis": [i.get("basis") for i in items],
        "long_short_ratio": [i.get("long_short_ratio") for i in items],
    })
    return frame.drop_duplicates("date").sort_values("date")[COLUMNS]


def panel_name(saved):
    """binance_LUNAUSDT.csv from BINANCE_LUNAUSDT.json, matching the panel."""
    market, instrument = saved.split("_", 1)
    return f"{market.lower()}_{instrument[:-5]}.csv"


def merge(store, panel, out):
    """Copy the panel, then add a file for every saved name that has bars.

    Returns the counts. A name whose panel file already exists is not
    overwritten: the catalogue copy is the one the daily append refreshes.
    """
    os.makedirs(out, exist_ok=True)
    copied = 0
    for name in sorted(os.listdir(panel)):
        if name.endswith(".csv"):
            shutil.copyfile(os.path.join(panel, name), os.path.join(out, name))
            copied += 1
    added, skipped_present, skipped_empty = [], [], []
    for name in sorted(os.listdir(store)):
        if not name.endswith(".json"):
            continue
        target = panel_name(name)
        if os.path.exists(os.path.join(out, target)):
            skipped_present.append(name)
            continue
        frame = frame_of(json.load(open(os.path.join(store, name))))
        if frame is None:
            skipped_empty.append(name)
            continue
        tmp = os.path.join(out, target + ".tmp")
        frame.to_csv(tmp, index=False)
        os.replace(tmp, os.path.join(out, target))
        added.append({"file": name, "panel": target, "bars": int(len(frame)),
                      "first": frame["date"].iloc[0], "last": frame["date"].iloc[-1]})
    return {"copied": copied, "added": added,
            "skipped_present": skipped_present, "skipped_empty": skipped_empty}


def main():
    counts = merge(STORE, PANEL, OUT)
    print(json.dumps({"copied": counts["copied"], "added": len(counts["added"]),
                      "skipped_present": len(counts["skipped_present"]),
                      "skipped_empty": len(counts["skipped_empty"]),
                      "out": OUT}))
    for row in counts["added"][:5]:
        print(json.dumps(row))


if __name__ == "__main__":
    import json
    main()
