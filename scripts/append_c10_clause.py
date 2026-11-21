"""Add the Done-when clause to the C10 line.

The clause is copied from research/RESEARCH_PROGRAM_CYCLE.md section 6 and
the weekly layer line in section 4. It is committed alone, before the item
is claimed.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
CLAUSE = (
    " Done when a committed script scores the weekly cycle layer at horizons "
    "of 12 and 26 weeks; results/<date>_c10_weekly.json is written by that "
    "script through write_result and states the weekly sample size beside "
    "each cell; a cell below 30 episodes across train and validation is "
    "insufficient."
)


def main():
    text = open(PATH).read()
    line = next(ln for ln in text.splitlines() if ln.startswith("- C10. "))
    if "Done when" in line:
        raise SystemExit("clause already present")
    open(PATH, "w").write(text.replace(line, line.rstrip("\n") + CLAUSE + "\n", 1))
    print("clause added")


if __name__ == "__main__":
    main()
