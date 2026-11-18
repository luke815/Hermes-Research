"""Point-in-time universe from the exchange span files.

A name is listed on a date when that date falls between its first and last
archive file. Binance publishes no stopped flag, so a name whose last file is
before the span pull date is delisted, the same rule the other two exchanges
record explicitly. The cutoff is read from the span files, never typed.
"""

import csv
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SPAN_FILES = {
    "binance": ROOT / "data" / "binance_span.csv",
    "bybit": ROOT / "data" / "bybit_span.csv",
    "okx": ROOT / "data" / "okx_span.csv",
}


def span_rows(directory=None):
    """One row per name, with listed_from, listed_to and whether it was delisted.

    directory overrides the span location, so a test can plant its own files.
    """
    files = SPAN_FILES if directory is None else {
        name: Path(directory) / f"{name}_span.csv" for name in SPAN_FILES}
    rows = []
    for exchange, path in files.items():
        if not path.exists():
            continue
        with open(path) as handle:
            for raw in csv.DictReader(handle):
                rows.append({
                    "exchange": exchange,
                    "symbol": raw["symbol"],
                    "listed_from": raw["first"][:10],
                    "listed_to": raw["last"][:10],
                })
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    cutoff = frame["listed_to"].max()
    frame["delisted"] = (frame["listed_to"] < cutoff).astype(int)
    return frame.sort_values(["exchange", "symbol"]).reset_index(drop=True)


def listed_on(universe, date):
    """Names whose span covers the date. A name that listed later is absent."""
    day = str(date)[:10]
    mask = (universe["listed_from"] <= day) & (universe["listed_to"] >= day)
    return universe[mask]


def delisted_by_date(universe):
    """How many delisted names are still inside their span on each date."""
    dead = universe[universe["delisted"] == 1]
    if dead.empty:
        return pd.DataFrame(columns=["date", "delisted_names"])
    start = datetime.fromisoformat(dead["listed_from"].min())
    end = datetime.fromisoformat(dead["listed_to"].max())
    counts = []
    day = start
    while day <= end:
        stamp = day.date().isoformat()
        inside = ((dead["listed_from"] <= stamp) & (dead["listed_to"] >= stamp)).sum()
        counts.append({"date": stamp, "delisted_names": int(inside)})
        day += timedelta(days=1)
    return pd.DataFrame(counts)
