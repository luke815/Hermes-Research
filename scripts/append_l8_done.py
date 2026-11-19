"""Append the L8 done line that done_check printed."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "What remains is the done_check close, which needs a claim of its own."
NOTE = " Done 2026-11-19. done_check eeae0e5275."


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
