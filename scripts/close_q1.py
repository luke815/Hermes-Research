"""Append the Q1 closing line that done_check printed.

The token comes from the check this run ran. This script only writes the line.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
LINE = "Done 2026-11-21. done_check 48a26e899e."


def main():
    text = open(PATH).read()
    if LINE in text:
        raise SystemExit("closing line already present")
    lines = text.splitlines()
    at = next(i for i, line in enumerate(lines) if line.startswith("- Q1. "))
    lines[at] = lines[at] + " " + LINE
    open(PATH, "w").write("\n".join(lines) + "\n")
    print("closed")


if __name__ == "__main__":
    main()
