"""Append this run's reading of A5 to its backlog line."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "Unblocks when that file shows full_day true."
NOTE = (" Rechecked 2026-11-19 23:00 UTC: results/2026-11-19_a5_span.json shows "
        "full_day false, false_span_hours 10.12 over 75 readings, newest "
        "2026-11-19T23:11:38Z, rs_stale false. The span starts "
        "2026-11-19T13:04:19Z, so a full day cannot be shown yet. Blocked on "
        "the clock. Unblocks when that file shows full_day true.")


def main():
    text = open(PATH).read()
    if "false_span_hours 10.12" in text:
        raise SystemExit("note already present")
    count = text.count(ANCHOR)
    if count < 1:
        raise SystemExit(f"anchor count {count}")
    open(PATH, "w").write(text.replace(ANCHOR, ANCHOR + NOTE, 1))
    print("appended", count)


if __name__ == "__main__":
    main()
