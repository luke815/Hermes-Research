"""Record that A7(1) was not scored this run. No number is computed."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "Done per test with its results file and verdict."
NOTE = (
    " Not scored 2026-11-20: scripts/score_a7_reversal.py is committed and "
    "reads data/panel_xs_laevitas, and no results file was written. Three runs "
    "ended at the 600 second limit while reading the 5,538 files, the last at "
    "file 5,000 after 529 seconds. The pre-registration is commit 2d78832."
)


def main():
    text = open(PATH).read()
    line = next(ln for ln in text.splitlines() if ln.startswith("- A7. "))
    if "Not scored 2026-11-20" in line:
        raise SystemExit("note already present")
    if ANCHOR not in line:
        raise SystemExit("anchor missing")
    updated = line.replace(ANCHOR, ANCHOR + NOTE, 1)
    open(PATH, "w").write(text.replace(line, updated, 1))
    print("noted")


if __name__ == "__main__":
    main()
