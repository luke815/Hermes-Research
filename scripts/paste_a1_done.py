"""Paste the A1 done line that done_check printed.

The token comes from ops/done_checks/A1.json, which scripts/done_check.py
wrote. This script only copies that line onto the backlog, exactly as printed.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import done_check  # noqa: E402

BACKLOG = os.path.join(ROOT, "research", "backlog.md")
RECORD = os.path.join(ROOT, "ops", "done_checks", "A1.json")

ANCHOR = "and the results file is written by that script."


def main():
    record = json.load(open(RECORD))
    line = done_check.done_line(record)
    text = open(BACKLOG).read()
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    if line in text:
        raise SystemExit("paste line already present")
    open(BACKLOG, "w").write(text.replace(ANCHOR, ANCHOR + " " + line, 1))
    print(line)


if __name__ == "__main__":
    main()
