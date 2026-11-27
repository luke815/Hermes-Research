"""Remove the doubled period the R6 clause insert left behind.

R6's line had no second sentence, so the insert kept the title's period
and added another. This removes that one extra period and nothing else.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
BAD = "- R6. Weekly review added to the weekly note.. Done when "
GOOD = "- R6. Weekly review added to the weekly note. Done when "


def main():
    text = open(BACKLOG).read()
    if text.count(BAD) != 1:
        raise SystemExit(f"expected the doubled period once, found {text.count(BAD)}")
    open(BACKLOG, "w").write(text.replace(BAD, GOOD, 1))
    print("period removed")


if __name__ == "__main__":
    main()
