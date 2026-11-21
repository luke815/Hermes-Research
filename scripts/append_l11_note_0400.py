"""Record this run's reading of L11 on its backlog line.

The numbers come from results/2026-11-21_l11_coverage.json, written by
scripts/l11_coverage.py, and results/2026-11-21_l11_reading.json, written by
scripts/l11_reading.py. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
COVERAGE = os.path.join(ROOT, "results", "2026-11-21_l11_coverage.json")
READING = os.path.join(ROOT, "results", "2026-11-21_l11_reading.json")
ANCHOR = "Blocked on the vendor's start date."


def main():
    coverage = json.load(open(COVERAGE))
    reading = json.load(open(READING))
    text = open(PATH).read()
    marker = "Rechecked 2026-11-21 04:00 UTC: results/2026-11-21_l11_coverage.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- L11. "))
    if ANCHOR not in line:
        raise SystemExit("anchor missing from the L11 line")
    note = (
        " Rechecked 2026-11-21 04:00 UTC: results/2026-11-21_l11_coverage.json "
        f"counts {coverage['dead_names']} dead names, {coverage['panel_files']} "
        f"panel files, {coverage['missing_file']} missing, and "
        f"{coverage['all_three_from_2021']} names with funding, open interest "
        f"and basis from 2021, earliest {coverage['earliest_first_bar']}. "
        f"delisted_pull phase {reading['phase']}, cycles {reading['cycles']}, "
        f"remaining {reading['remaining']}. The vendor serves nothing earlier. "
        "Blocked on the vendor's start date."
    )
    updated = line.replace(ANCHOR, ANCHOR + note, 1)
    open(PATH, "w").write(text.replace(line, updated, 1))
    print("appended")


if __name__ == "__main__":
    main()
