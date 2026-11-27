"""Record the A5 reading on its backlog line.

The numbers come from results/2026-11-20_a5_span.json, written by
scripts/a5_span.py, and the closing line is the one done_check printed.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-20_a5_span.json")
ANCHOR = ("2026-11-20T13:04:19Z. Blocked on the clock. "
          "Unblocks when that file shows full_day true.")
DONE = "Done 2026-11-20. done_check e8e8e62a5c."


def main():
    reading = json.load(open(RESULT))
    if not reading["full_day"]:
        raise SystemExit("full_day is false; nothing to record")
    text = open(PATH).read()
    marker = f"false_span_hours {reading['false_span_hours']}"
    if marker in text:
        raise SystemExit("note already present")
    count = text.count(ANCHOR)
    if count != 1:
        raise SystemExit(f"anchor count {count}")
    note = (
        " Rechecked 2026-11-20 15:00 UTC: results/2026-11-20_a5_span.json shows "
        f"full_day true, false_span_hours {reading['false_span_hours']} over "
        f"{reading['readings']} readings, newest {reading['reading_ts']}, "
        f"rs_stale {str(reading['rs_stale']).lower()}, board_as_of "
        f"{reading['board_as_of']}. {DONE}"
    )
    open(PATH, "w").write(text.replace(ANCHOR, ANCHOR + note, 1))
    print("appended")


if __name__ == "__main__":
    main()
