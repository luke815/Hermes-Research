"""Append this run's reading of A5 to its backlog line.

The numbers come from results/2026-11-20_a5_span.json, written by
scripts/a5_span.py. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-20_a5_span.json")
ANCHOR = ("Rechecked 2026-11-20 11:00 UTC: results/2026-11-20_a5_span.json "
          "shows full_day false, false_span_hours 21.95 over 217 readings, "
          "newest 2026-11-20T11:01:36Z, rs_stale false, board_as_of "
          "2026-11-20T09:00:00Z. Blocked on the clock. Unblocks when that "
          "file shows full_day true.")


def main():
    reading = json.load(open(RESULT))
    if reading["full_day"]:
        raise SystemExit("span is a full day; this note is the blocked reading")
    if reading["reading_ts"] != "2026-11-20T13:00:23Z":
        raise SystemExit(f"unexpected reading {reading['reading_ts']}")
    text = open(PATH).read()
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    note = (
        " Rechecked 2026-11-20 13:00 UTC: results/2026-11-20_a5_span.json shows "
        f"full_day false, false_span_hours {reading['false_span_hours']} over "
        f"{reading['readings']} readings, newest {reading['reading_ts']}, "
        f"rs_stale {str(reading['rs_stale']).lower()}, board_as_of "
        f"{reading['board_as_of']}. The span starts 2026-11-19T13:04:19Z, so "
        "a full day needs a reading at or after 2026-11-20T13:04:19Z. Blocked "
        "on the clock. Unblocks when that file shows full_day true."
    )
    open(PATH, "w").write(text.replace(ANCHOR, ANCHOR + note, 1))
    print("appended")


if __name__ == "__main__":
    main()
