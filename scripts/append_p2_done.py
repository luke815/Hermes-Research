"""Paste the P2 done line exactly as done_check printed it."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
OLD = ("Done when pairs_board is in data.json; the key has the mean-reversion "
       "list and the relative-strength list.")
NEW = OLD + " Done 2026-11-19. done_check 806f077328."


def main():
    text = open(PATH).read()
    if "done_check 806f077328" in text:
        raise SystemExit("line already present")
    if text.count(OLD) != 1:
        raise SystemExit(f"anchor count {text.count(OLD)}")
    open(PATH, "w").write(text.replace(OLD, NEW, 1))
    print("pasted")


if __name__ == "__main__":
    main()
