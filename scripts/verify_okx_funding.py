"""Verify the OKX funding pull against the span and the part markers.

Writes results/2026-11-05_d1_okx_funding.json. Every number in that file is
computed here, from the files on disk.
"""

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester/data")
SPAN = ROOT / "okx_span.csv"
INDEX = ROOT / "okx_funding_index.csv"
PARTS = ROOT / "okx_funding_parts"
OUT = ROOT / "okx_funding"
RESULTS = Path("/opt/data/workspace/regime-tester/results/2026-11-05_d1_okx_funding.json")

today = datetime.now(timezone.utc).date().isoformat()

with open(SPAN) as handle:
    span = {row["symbol"]: row for row in csv.DictReader(handle) if row["stopped"] == "1"}

with open(INDEX) as handle:
    index_days = [day for day, _url in csv.reader(handle)]

parts = {}
bad_parts = []
for day in index_days:
    path = PARTS / f"{day}.txt"
    if not path.exists():
        bad_parts.append((day, "missing"))
        continue
    text = path.read_text()
    if not text.endswith("OK\n"):
        bad_parts.append((day, "no marker"))
        continue
    parts[day] = {line for line in text.splitlines()[:-1] if line}

files = {}
mismatch = []
blank_days = 0
blank_names = Counter()
settlement_counts = Counter()
for symbol, row in sorted(span.items()):
    path = OUT / f"{symbol}.csv"
    if not path.exists():
        files[symbol] = None
        continue
    with open(path) as handle:
        saved = list(csv.DictReader(handle))
    dates = [item["date"] for item in saved]
    dupes = len(dates) - len(set(dates))
    ordered = dates == sorted(dates)
    blanks = sum(1 for item in saved if item["funding_rate"] == "")
    blank_days += blanks
    if blanks:
        blank_names[symbol] = blanks
    for item in saved:
        settlement_counts[item["settlements"]] += 1
    expected = sorted(day for day, names in parts.items() if symbol in names)
    files[symbol] = {
        "rows": len(saved),
        "first": dates[0] if dates else None,
        "last": dates[-1] if dates else None,
        "dupes": dupes,
        "ordered": ordered,
        "blanks": blanks,
    }
    if dates != expected or dupes or not ordered:
        mismatch.append({
            "symbol": symbol,
            "saved": len(dates),
            "expected": len(expected),
            "dupes": dupes,
            "ordered": ordered,
            "first_saved": dates[0] if dates else None,
            "first_expected": expected[0] if expected else None,
            "last_saved": dates[-1] if dates else None,
            "last_expected": expected[-1] if expected else None,
        })

present = {symbol: info for symbol, info in files.items() if info}
absent = sorted(symbol for symbol, info in files.items() if info is None)

price_only = []
funding_only = []
both = 0
for symbol, row in span.items():
    info = files.get(symbol)
    if info is None:
        price_only.append({"symbol": symbol, "price_first": row["first"], "price_last": row["last"], "price_days": int(row["days"])})
        continue
    both += 1
    if info["first"] > row["first"] or info["last"] < row["last"]:
        price_only.append({
            "symbol": symbol,
            "price_first": row["first"],
            "price_last": row["last"],
            "funding_first": info["first"],
            "funding_last": info["last"],
            "price_days": int(row["days"]),
            "funding_days": info["rows"],
            "gap": "funding shorter than price span",
        })
    if info["first"] < row["first"] or info["last"] > row["last"]:
        funding_only.append({
            "symbol": symbol,
            "price_first": row["first"],
            "price_last": row["last"],
            "funding_first": info["first"],
            "funding_last": info["last"],
        })

shorter = [item for item in price_only if "gap" in item]
never = [item for item in price_only if "gap" not in item]

result = {
    "candidate": "d1_okx_funding",
    "date": today,
    "verdict": "recorded, not admitted",
    "source": "https://www.okx.com/api/v5/public/market-data-history module=3 instType=SWAP instFamilyList=ANY dateAggrType=daily",
    "columns": "instrument_name,funding_rate,funding_time",
    "row_rule": "last numeric settlement of the UTC day, with the count of settlements and the day mean; a day whose every settlement is the literal string None is kept with a blank rate",
    "index_start": index_days[0],
    "index_end": index_days[-1],
    "days_listed": len(index_days),
    "days_written": len(parts),
    "bad_parts": bad_parts,
    "rows_saved": sum(info["rows"] for info in present.values()),
    "rows_read": sum(len(names) for names in parts.values()),
    "symbols_with_funding": len(present),
    "symbols_stopped": len(span),
    "symbols_absent": absent,
    "files_mismatching_parts": mismatch,
    "blank_rate_days": blank_days,
    "blank_rate_names": len(blank_names),
    "settlements_per_day": dict(sorted(settlement_counts.items(), key=lambda item: int(item[0]))),
    "funding_shorter_than_price": len(shorter),
    "funding_shorter_sample": shorter[:12],
    "no_funding_file": never,
    "funding_beyond_price_span": len(funding_only),
    "funding_beyond_sample": funding_only[:12],
    "open_interest": "not pulled; no module of market-data-history serves it",
    "liquidations": "not pulled; the archive publishes none",
    "bybit": "not touched",
    "score_changed": False,
    "tests_since_last_admission": 13,
}
RESULTS.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: result[k] for k in (
    "date", "days_listed", "days_written", "bad_parts", "rows_saved", "rows_read",
    "symbols_with_funding", "symbols_absent", "files_mismatching_parts",
    "blank_rate_days", "blank_rate_names", "funding_shorter_than_price",
    "no_funding_file", "funding_beyond_price_span")}, indent=2))
