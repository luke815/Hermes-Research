"""Rebuild the panel files whose vendor price field jumps while the index holds.

scripts/count_price_jumps.py names the files. This reads that results file,
rebuilds only those names into a sibling directory with closes_of, and leaves
the live panel untouched. The swap is a separate step.
"""

import json
import os
import shutil
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_universe_laevitas as builder  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "data", "laevitas", "perpetuals")
SRC = os.path.join(ROOT, "data", "panel_xs_laevitas")
OUT = os.path.join(ROOT, "data", "panel_xs_laevitas_fixed5")
JUMPS = os.path.join(ROOT, "results", "2026-11-21_a7_price_jumps.json")


def main():
    if os.path.exists(OUT):
        raise SystemExit(f"{OUT} already exists")
    reading = json.loads(open(JUMPS).read())
    panel = {name.lower(): name for name in os.listdir(SRC)}
    sources = {}
    for row in reading["affected"]:
        want = row["file"][:-5].lower() + ".csv"
        real = panel.get(want)
        if real is None:
            raise SystemExit(f"no panel file for {row['file']}")
        sources[row["file"]] = real
    shutil.copytree(SRC, OUT, copy_function=os.link)
    rebuilt = 0
    for source_name, panel_name in sorted(sources.items()):
        source = os.path.join(STORE, source_name)
        body = json.loads(open(source).read())
        items = sorted(
            (i for i in body.get("items", []) if i.get("price") is not None),
            key=lambda i: i["date"])
        frame = pd.DataFrame({
            "date": [builder.day(i["date"]) for i in items],
            "close": builder.closes_of(items),
            "volume_usd": [i.get("volume") for i in items],
            "volume_base": [i.get("volume_coin") for i in items],
            "funding_rate": [i.get("funding") for i in items],
            "oi_usd": [i.get("open_interest") for i in items],
            "basis": [i.get("basis") for i in items],
            "long_short_ratio": [i.get("long_short_ratio") for i in items],
        }).drop_duplicates("date").sort_values("date")
        existing = os.path.join(SRC, panel_name)
        header = open(existing).readline().rstrip("\n").split(",")
        extra = [col for col in header if col not in frame.columns]
        if extra:
            prior = pd.read_csv(existing, usecols=["date"] + extra)
            frame = frame.merge(prior, on="date", how="left")
            frame = frame[list(frame.columns[:8]) + extra]
        tmp = os.path.join(OUT, panel_name + ".tmp")
        frame.to_csv(tmp, index=False)
        os.replace(tmp, os.path.join(OUT, panel_name))
        rebuilt += 1
    print(f"rebuilt {rebuilt} of {len(sources)} into {OUT}")
    pepe = os.path.join(OUT, "binance_1000PEPEUSDT.csv")
    for line in open(pepe):
        if line.startswith("2026-01-1"):
            print("PEPE", line.strip())


if __name__ == "__main__":
    main()
