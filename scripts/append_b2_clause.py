"""Add the Done-when clause to the B2 line.

The clause is copied from research/LONG_SHORT_BOOK.md sections 2, 3, 4 and 8.
It is committed alone, before the item is claimed.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
CLAUSE = (
    " Done when a committed script writes the provisional composite and the "
    "two legs; results/<date>_b2_book.json is written by that script through "
    "write_result and names the components, the weights and the names in each "
    "leg; the book key in dashboard/data.json carries status provisional with "
    "the same as_of; signals/book.csv records the first paper rebalance."
)


def main():
    text = open(PATH).read()
    line = next(ln for ln in text.splitlines() if ln.startswith("- B2. "))
    if "Done when" in line:
        raise SystemExit("clause already present")
    updated = line.rstrip("\n") + CLAUSE
    open(PATH, "w").write(text.replace(line, updated + "\n", 1))
    print("clause added")


if __name__ == "__main__":
    main()
