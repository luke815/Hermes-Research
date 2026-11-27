"""Paste the done_check line onto the C10 backlog line.

The line is exactly what scripts/done_check.py printed. This script only
writes it.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
LINE = "Done 2026-11-21. done_check 6e47fb0d5e."


def main():
    text = open(PATH).read()
    line = next(ln for ln in text.splitlines() if ln.startswith("- C10. "))
    if LINE in line:
        raise SystemExit("line already present")
    open(PATH, "w").write(text.replace(line, line.rstrip("\n") + " " + LINE + "\n", 1))
    print("pasted")


if __name__ == "__main__":
    main()
