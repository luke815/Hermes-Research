"""Append the E3 note, citing the results file written this run."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "Done when the hosted key has every list."
NOTE = (" Built 2026-11-19: scripts/build_extremes.py wrote all ten lists, as_of 2026-11-16, 109 names above the floor. Not done: results/2026-11-19_e3_extremes.json shows the raw file on main matches the local key and the hosted page returns 404, so the hosted key cannot be confirmed.")


def main():
    text = open(BACKLOG).read()
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    open(BACKLOG, "w").write(text.replace(ANCHOR, ANCHOR + NOTE, 1))
    print("backlog updated", os.path.getsize(BACKLOG))


if __name__ == "__main__":
    main()
