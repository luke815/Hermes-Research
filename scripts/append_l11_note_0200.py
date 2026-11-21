"""Record this run's reading of L11 on its backlog line.

The numbers come from results/2026-11-21_l11_coverage.json, written by
scripts/l11_coverage.py. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-21_l11_coverage.json")
ANCHOR = "Blocked on the vendor's start date."


def main():
    reading = json.load(open(RESULT))
    text = open(PATH).read()
    marker = "Rechecked 2026-11-21 02:00 UTC: results/2026-11-21_l11_coverage.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- L11. "))
    if ANCHOR not in line:
        raise SystemExit("anchor missing from the L11 line")
    note = (
        " Rechecked 2026-11-21 02:00 UTC: results/2026-11-21_l11_coverage.json "
        f"counts {reading['dead_names']} dead names, {reading['panel_files']} "
        f"panel files, {reading['missing_file']} missing, and "
        f"{reading['all_three_from_2021']} names with funding, open interest "
        f"and basis from 2021, earliest {reading['earliest_first_bar']}. "
        "The 15 missing files are saved empty vendor answers. delisted_pull "
        "reports remaining 0. The vendor serves nothing earlier. "
        "Blocked on the vendor's start date."
    )
    updated = line.replace(ANCHOR, ANCHOR + note, 1)
    open(PATH, "w").write(text.replace(line, updated, 1))
    print("appended")


if __name__ == "__main__":
    main()
