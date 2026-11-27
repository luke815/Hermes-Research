"""Put the P4 done-when clause on its item line.

The clause names the pre-registration file and the results file. This script
only edits the backlog line.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
OLD = ("Done when PREREG4.md is committed before any cell is scored and the\n"
       "  results are written by write_result.")
NEW = ("Done when research/outside/PREREG4.md is committed before any cell is "
       "scored; results/<date>_p4_cells.json is written by write_result and "
       "carries a verdict for A1, A2, A3 and A6 and the A5 transition matrix "
       "with no verdict.")


def main():
    text = open(PATH).read()
    if text.count(OLD) != 1:
        raise SystemExit(f"anchor count {text.count(OLD)}")
    open(PATH, "w").write(text.replace(OLD, NEW, 1))
    print("rewritten")


if __name__ == "__main__":
    main()
