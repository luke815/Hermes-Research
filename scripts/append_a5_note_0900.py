"""Append this run's reading of A5 to its backlog line.

The numbers come from results/2026-11-20_a5_span.json, written by
scripts/a5_span.py. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-20_a5_span.json")
ANCHOR = "Unblocks when that file shows full_day true."


def main():
    reading = json.load(open(RESULT))
    if reading["full_day"]:
        raise SystemExit("span is a full day; this note is the blocked reading")
    text = open(PATH).read()
    marker = f"false_span_hours {reading['false_span_hours']}"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- A5. "))
    if line.count(ANCHOR) < 1:
        raise SystemExit("anchor missing from the A5 line")
    note = (
        " Rechecked 2026-11-20 09:00 UTC: results/2026-11-20_a5_span.json shows "
        f"full_day false, false_span_hours {reading['false_span_hours']} over "
        f"{reading['readings']} readings, newest {reading['reading_ts']}, "
        f"rs_stale {str(reading['rs_stale']).lower()}, board_as_of "
        f"{reading['board_as_of']}. Blocked on the clock. "
        "Unblocks when that file shows full_day true."
    )
    updated = line.replace(ANCHOR, ANCHOR + note, 1)
    open(PATH, "w").write(text.replace(line, updated, 1))
    print("appended")


if __name__ == "__main__":
    main()
