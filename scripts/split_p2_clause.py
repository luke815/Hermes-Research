"""Split the P2 done-when clause into the two parts it names."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
OLD = ("Done when pairs_board is in data.json with the mean-reversion and "
       "relative-strength lists.")
NEW = ("Done when pairs_board is in data.json; the key has the mean-reversion "
       "list and the relative-strength list.")


def main():
    text = open(PATH).read()
    if text.count(OLD) != 1:
        raise SystemExit(f"anchor count {text.count(OLD)}")
    open(PATH, "w").write(text.replace(OLD, NEW, 1))
    print("rewritten")


if __name__ == "__main__":
    main()
