"""Verify the 2024-01-01 to 2025-06-03 OKX stopped-name price slice.

Reads the part files, the saved CSVs and data/okx_span.csv, and writes
results/<today>_d1_okx_prices_2024.json. No return is scored.
"""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester")
DATA = ROOT / "data"
PARTS = DATA / "okx_price_parts"
OUT = DATA / "okx_prices"
START = "2024-01-01"
DAYS = 520


def main() -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    with open(DATA / "okx_index.csv", newline="") as handle:
        index = [day for day, _ in csv.reader(handle) if day >= START][:DAYS]
    if index[0] != START or len(index) != DAYS:
        raise SystemExit(f"window mismatch: {len(index)} days from {index[0]}")
    end = index[-1]

    missing, bad, part_rows = [], [], {}
    for day in index:
        path = PARTS / f"{day}.txt"
        if not path.exists():
            missing.append(day)
            continue
        text = path.read_text()
        if not text.endswith("\nOK\n"):
            bad.append(day)
            continue
        part_rows[day] = text.count("\n") - 1

    span = {}
    with open(DATA / "okx_span.csv", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["stopped"] == "1":
                span[row["symbol"]] = row

    per_symbol = []
    saved_rows = 0
    short_bar_days = 0
    full_bar_days = 0
    mismatches = []
    for symbol in sorted(span):
        path = OUT / f"{symbol}.csv"
        if not path.exists():
            continue
        with open(path, newline="") as handle:
            rows = list(csv.DictReader(handle))
        in_window = [row for row in rows if START <= row["date"] <= end]
        if not in_window:
            continue
        dates = [row["date"] for row in in_window]
        if dates != sorted(dates) or len(dates) != len(set(dates)):
            mismatches.append(f"{symbol}: dates not unique and ordered")
        first, last = dates[0], dates[-1]
        record = span[symbol]
        complete = last == record["last"] and first == record["first"]
        if first != record["first"] and record["first"] >= START:
            mismatches.append(f"{symbol}: first {first} != span {record['first']}")
        if complete and str(len(dates)) != record["days"]:
            mismatches.append(f"{symbol}: {len(dates)} days != span {record['days']}")
        if last > record["last"]:
            mismatches.append(f"{symbol}: saved past span last {record['last']}")
        short = sum(1 for row in in_window if row["bars"] != "1440")
        short_bar_days += short
        full_bar_days += len(in_window) - short
        saved_rows += len(in_window)
        per_symbol.append({
            "symbol": symbol,
            "rows": len(in_window),
            "first": first,
            "last": last,
            "span_first": record["first"],
            "span_last": record["last"],
            "span_days": int(record["days"]),
            "complete": complete,
            "short_bar_days": short,
        })

    part_total = sum(part_rows.values())
    if part_total != saved_rows:
        mismatches.append(f"part rows {part_total} != saved rows {saved_rows}")

    result = {
        "candidate": "d1_okx_prices_2024",
        "date": today,
        "verdict": "recorded, not admitted",
        "window": [START, end],
        "index_days": len(index),
        "missing_days": missing,
        "bad_marker_days": bad,
        "failed_days": len(missing) + len(bad),
        "stopped_symbols_in_span": len(span),
        "symbols_saved_in_window": len(per_symbol),
        "symbols_complete": sum(1 for row in per_symbol if row["complete"]),
        "symbols_continuing_past_window": sum(1 for row in per_symbol if not row["complete"]),
        "rows": saved_rows,
        "part_rows": part_total,
        "short_bar_days": short_bar_days,
        "full_bar_days": full_bar_days,
        "mismatches": mismatches,
        "per_symbol": per_symbol,
    }
    target = ROOT / "results" / f"{today}_d1_okx_prices_2024.json"
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(f"wrote {target}")
    print(f"window {START}..{end} days={len(index)} failed={result['failed_days']}")
    print(f"symbols={len(per_symbol)} complete={result['symbols_complete']} continuing={result['symbols_continuing_past_window']}")
    print(f"rows={saved_rows} part_rows={part_total} short_bar_days={short_bar_days}")
    print(f"mismatches={len(mismatches)}")
    for item in mismatches[:10]:
        print(f"  {item}")


if __name__ == "__main__":
    main()
