"""Record the P3 close on its backlog line.

The token comes from done_check. This script only records it.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "left null otherwise."


def main():
    text = open(PATH).read()
    marker = "Done 2026-11-21. done_check f0f5ebae46."
    if marker in text:
        raise SystemExit("already recorded")
    lines = text.splitlines(keepends=True)
    index = next(i for i, ln in enumerate(lines) if ANCHOR in ln)
    lines[index] = lines[index].rstrip("\n") + " " + marker + "\n"
    open(PATH, "w").write("".join(lines))
    print("recorded")


if __name__ == "__main__":
    main()
