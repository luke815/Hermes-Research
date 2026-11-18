"""Per-symbol hourly bar store at data/intraday/<symbol>.csv.

Each file is t,o,h,l,c,v. Writes go to a temp file and rename, so a killed run
leaves the previous complete file rather than a partial one. Appending dedupes
on the bar timestamp, and the last bar is the one the vendor last sent.
"""

import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "data", "intraday")
FIELDS = ["t", "o", "h", "l", "c", "v"]


def path_for(symbol, store=None):
    safe = symbol.replace("/", "_")
    return os.path.join(store or STORE, safe + ".csv")


def read(symbol, store=None):
    path = path_for(symbol, store)
    if not os.path.exists(path):
        return []
    with open(path) as fh:
        return [{k: float(row[k]) if k != "t" else int(row[k]) for k in FIELDS}
                for row in csv.DictReader(fh)]


def write(symbol, bars, store=None):
    """Replace the file atomically. bars is a list of dicts with FIELDS."""
    target = store or STORE
    os.makedirs(target, exist_ok=True)
    path = path_for(symbol, target)
    tmp = path + ".tmp"
    ordered = sorted({b["t"]: b for b in bars}.values(), key=lambda b: b["t"])
    with open(tmp, "w", newline="") as fh:
        out = csv.DictWriter(fh, fieldnames=FIELDS)
        out.writeheader()
        for b in ordered:
            out.writerow({k: b[k] for k in FIELDS})
    os.replace(tmp, path)
    return len(ordered)


def append(symbol, bars, store=None):
    """Add bars, dedupe by timestamp, rewrite atomically. Returns the new length."""
    return write(symbol, read(symbol, store) + list(bars), store)


def symbols():
    if not os.path.isdir(STORE):
        return []
    return sorted(f[:-4] for f in os.listdir(STORE) if f.endswith(".csv"))


def seed_from(payload):
    """Seed the store from a Coinalyze ohlcv-history payload already on disk.

    A symbol that already has rows is left untouched, so seeding is safe to repeat.
    """
    seeded = 0
    for row in payload["rows"]:
        if read(row["symbol"]):
            continue
        bars = [{"t": b["t"], "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "v": b["v"]}
                for b in row.get("history", [])]
        if bars:
            write(row["symbol"], bars)
            seeded += 1
    return seeded
