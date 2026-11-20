"""Append this run's D1 close to its backlog line.

The token is passed in, because done_check prints it and this script only
writes the line. It refuses to run twice.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "table shows a note on liq_*."
NOTE = (" Done 2026-11-20. done_check {token}. The cause is written in "
        "data/COVERAGE.md and recomputed by scripts/d1_coverage.py: the 2026 "
        "rise is in the vendor file, one symbol, continuous from 2022-09-09, "
        "and the daily total drifts rather than steps. "
        "results/2026-11-20_d1_coverage.json. scripts/build_data_json.py now "
        "writes the note on the Liquidations row of the health table, "
        "tests/test_build_data_json.py CoverageNote.")


def main():
    token = sys.argv[1]
    text = open(PATH).read()
    if "results/2026-11-20_d1_coverage.json" in text:
        raise SystemExit("note already present")
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    open(PATH, "w").write(text.replace(ANCHOR, ANCHOR + NOTE.format(token=token), 1))
    print("appended")


if __name__ == "__main__":
    main()
