"""Append the A5 progress note, citing the results file written this run."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "Done when live.json's health.rs_stale is false for a full day, which needs the live daemon restarted onto this commit."
NOTE = (" Read 2026-11-19: results/2026-11-19_a5_state.json shows rs_stale false, newest hourly bar 2026-11-18T22:00:00Z, age 7,460 seconds against the 10,800 second window, 99 of 100 files current and one name stopped at 2026-11-05. The full day has not elapsed, so the item stays open.")


def main():
    text = open(BACKLOG).read()
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    open(BACKLOG, "w").write(text.replace(ANCHOR, ANCHOR + NOTE, 1))
    print("backlog updated", os.path.getsize(BACKLOG))


if __name__ == "__main__":
    main()
