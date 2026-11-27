"""Mark the G30 line with the done_check token.

The token is the one scripts/done_check.py printed. This script writes that
line and nothing else.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
OLD = "- G30. "
NEW = "- G30. Done 2026-11-22. done_check 9c7faa9f82. "


def main():
    text = open(PATH).read()
    if text.count(OLD) != 1:
        raise SystemExit(f"anchor count {text.count(OLD)}")
    if "done_check 9c7faa9f82" in text:
        raise SystemExit("token already present")
    open(PATH, "w").write(text.replace(OLD, NEW, 1))
    print("marked")


if __name__ == "__main__":
    main()
