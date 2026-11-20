"""Paste the done_check line onto the P1 backlog line, exactly as printed."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "closes are the last 250 days from the venue with the most days above the floor."
LINE = " Done 2026-11-19. done_check 75ad75a741."


def main():
    text = open(PATH).read()
    if "done_check 75ad75a741" in text:
        raise SystemExit("already pasted")
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    open(PATH, "w").write(text.replace(ANCHOR, ANCHOR + LINE, 1))
    print("pasted")


if __name__ == "__main__":
    main()
