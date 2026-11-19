"""Paste the X2 done_check line into the backlog."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "Done when both lines cite the same file and the same number."
LINE = " Done 2026-11-19. done_check 5cf285dfcb."


def main():
    text = open(PATH).read()
    if "done_check 5cf285dfcb" in text:
        raise SystemExit("line already present")
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    open(PATH, "w").write(text.replace(ANCHOR, ANCHOR + LINE, 1))
    print("appended")


if __name__ == "__main__":
    main()
