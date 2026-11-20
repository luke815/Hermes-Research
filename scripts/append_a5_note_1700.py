"""Append this run's reading of A5 to its backlog line."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "Unblocks when that file shows full_day true."
NOTE = (" Rechecked 2026-11-19 17:00 UTC: results/2026-11-19_a5_span.json shows "
        "full_day false, false_span_hours 0.0 over 1 reading at "
        "2026-11-19T13:04:19Z. The live daemon rewrites live.json each cycle and "
        "nothing recorded the readings between runs, so the hours were not "
        "observed. scripts/live_daemon.py now appends each reading, restarted as "
        "pid 8553 version 3d9d9a4. Blocked: the span log cannot show 24 hours "
        "until those readings exist. Unblocks when that file shows full_day true.")


def main():
    text = open(PATH).read()
    if NOTE.strip() in text:
        raise SystemExit("note already present")
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    open(PATH, "w").write(text.replace(ANCHOR, ANCHOR + NOTE, 1))
    print("appended")


if __name__ == "__main__":
    main()
