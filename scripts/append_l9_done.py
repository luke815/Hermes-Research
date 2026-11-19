"""Record the L9 done line exactly as done_check printed it."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "Done when each series has first date, last date and missing-day count in data/INVENTORY.md, which the daemon writes when the walk finishes."
LINE = " Done 2026-11-19. done_check 38038277ec."


def main():
    text = open(BACKLOG).read()
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    if "done_check 38038277ec" in text:
        raise SystemExit("token already present")
    open(BACKLOG, "w").write(text.replace(ANCHOR, ANCHOR + LINE, 1))
    print("backlog updated", os.path.getsize(BACKLOG))


if __name__ == "__main__":
    main()
