"""Append this run's reading of L11 to its backlog line.

The coverage file was written by scripts/l11_coverage.py in this run.
The daemon's heartbeat is read here, not typed.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
COVERAGE = os.path.join(ROOT, "results", "2026-11-21_l11_coverage.json")
BEAT = os.path.join(ROOT, "ops", "delisted_pull_heartbeat")
ANCHOR = "The pre-registration is commit 2d78832."


def main():
    reading = json.loads(open(COVERAGE).read())
    beat = json.loads(open(BEAT).read())
    note = (
        f" Rechecked {reading['today']} 19:00 UTC: "
        f"results/{reading['today']}_l11_coverage.json counts "
        f"{reading['dead_names']} dead names, {reading['panel_files']} panel "
        f"files, {reading['missing_file']} missing, and "
        f"{reading['all_three_from_2021']} names with funding, open interest "
        f"and basis from 2021, earliest {reading['earliest_first_bar']}. "
        f"delisted_pull pid {beat.get('pid')}, alive, phase {beat.get('phase')}, "
        f"cycles {beat.get('cycles')}, remaining {beat.get('remaining')}. The "
        f"vendor serves nothing earlier. Blocked on the vendor's start date.")
    text = open(PATH).read()
    if note.strip() in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- L11. "))
    if not line.endswith("Blocked on the vendor's start date."):
        raise SystemExit("the L11 line no longer ends on the block sentence")
    open(PATH, "w").write(text.replace(line, line + note, 1))
    print("appended", reading["all_three_from_2021"], beat.get("remaining"))


if __name__ == "__main__":
    main()
