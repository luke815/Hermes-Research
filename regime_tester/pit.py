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


def listing_mask(index, columns, spans):
    """True where a name's span covers the date. A name with no span is out.

    spans maps a column to (listed_from, listed_to), both YYYY-MM-DD. A name
    that listed later, or whose last file is already past, is False on that
    date, so a rank computed on the masked frame cannot see it.
    """
    if isinstance(index, pd.DatetimeIndex):
        dates = index.strftime("%Y-%m-%d")
    else:
        dates = pd.Index([str(d)[:10] for d in index])
    out = pd.DataFrame(False, index=index, columns=list(columns))
    for column in columns:
        if column not in spans:
            continue
        start, end = spans[column]
        out[column] = (dates >= start) & (dates <= end)
    return out


def apply_listing_mask(frame, spans):
    """Set a name to NaN on dates outside its span. None leaves the frame as is."""
    if spans is None or frame is None or len(frame) == 0:
        return frame
    mask = listing_mask(frame.index, frame.columns, spans)
    return frame.where(mask)


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
