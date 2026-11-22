"""Append the 02:00 reading of L11 to its backlog line.

The numbers come from results/2026-11-22_l11_coverage.json and
results/2026-11-22_l11_reading.json, both written by their scripts. This
script only records the reading. It does not decide the item is done.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
COVERAGE = os.path.join(ROOT, "results", "2026-11-22_l11_coverage.json")
READING = os.path.join(ROOT, "results", "2026-11-22_l11_reading.json")


def main():
    coverage = json.loads(open(COVERAGE).read())
    reading = json.loads(open(READING).read())
    note = (
        f" Rechecked {coverage['today']} 02:00 UTC: "
        f"results/{coverage['today']}_l11_coverage.json counts "
        f"{coverage['dead_names']} dead names, {coverage['panel_files']} panel "
        f"files, {coverage['missing_file']} missing, and "
        f"{coverage['all_three_from_2021']} names with funding, open interest "
        f"and basis from 2021, earliest {coverage['earliest_first_bar']}. "
        f"results/{reading['today']}_l11_reading.json shows remaining "
        f"{reading['remaining']} of {reading['dead_names']}. delisted_pull "
        f"phase {reading['phase']}, cycles {reading['cycles']}, remaining "
        f"{reading['daemon_remaining']}. The vendor serves nothing earlier. "
        f"Blocked on the vendor's start date.")
    text = open(PATH).read()
    if note.strip() in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- L11. "))
    if not line.endswith("Blocked on the vendor's start date."):
        raise SystemExit("the L11 line no longer ends on the block sentence")
    open(PATH, "w").write(text.replace(line, line + note, 1))
    print("appended", coverage["all_three_from_2021"], reading["remaining"])


if __name__ == "__main__":
    main()
