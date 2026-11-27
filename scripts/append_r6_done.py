"""Paste the done_check line onto the R6 backlog item.

The line is exactly what done_check printed. This script only records it.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
LINE = "Done 2026-11-21. done_check 8d5def58b9."


def main():
    text = open(BACKLOG).read()
    if LINE in text:
        raise SystemExit("line already present")
    item = next(ln for ln in text.splitlines() if ln.startswith("- R6. "))
    if "Done when" not in item:
        raise SystemExit("the R6 line has no clause to close")
    open(BACKLOG, "w").write(text.replace(item, item + " " + LINE, 1))
    print("pasted")


if __name__ == "__main__":
    main()
