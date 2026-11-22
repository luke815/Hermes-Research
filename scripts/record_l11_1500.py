"""Record the 15:00 reading of L11.

The counts come from results/2026-11-22_l11_coverage.json, written by
scripts/l11_coverage.py, and the remaining count comes from the
delisted_pull heartbeat. This script records that reading. It does not
pull and it does not decide the item is done.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
COVERAGE = os.path.join(ROOT, "results", "2026-11-22_l11_coverage.json")
HEARTBEAT = os.path.join(ROOT, "ops", "delisted_pull_heartbeat")
ANCHOR = "Blocked on the vendor's start date."
SLOT = "2026-11-22 15:00"


def main():
    coverage = json.load(open(COVERAGE))
    beat = json.load(open(HEARTBEAT))
    out = {
        "item": "L11",
        "slot": SLOT,
        "dead_names": coverage["dead_names"],
        "panel_files": coverage["panel_files"],
        "missing_file": coverage["missing_file"],
        "all_three_from_2021": coverage["all_three_from_2021"],
        "earliest_first_bar": coverage["earliest_first_bar"],
        "daemon_pid": beat.get("pid"),
        "phase": beat.get("phase"),
        "cycles": beat.get("cycles"),
        "remaining": beat.get("remaining"),
        "unchanged_since": "2026-11-22 13:00",
        "blocked": "vendor start date",
        "unblocks": (
            "a vendor history earlier than 2021-08-07 for the dead names, "
            "which a research run does not pull"),
    }
    path = write_result(
        "l11_reading_1500", out,
        inputs=["results/2026-11-22_l11_coverage.json",
                "ops/delisted_pull_heartbeat"])
    note = (
        f" Rechecked {SLOT} UTC: results/2026-11-22_l11_coverage.json counts "
        f"{out['dead_names']} dead names, {out['panel_files']} panel files, "
        f"{out['missing_file']} missing, and {out['all_three_from_2021']} "
        f"names with funding, open interest and basis from 2021, earliest "
        f"{out['earliest_first_bar']}. results/2026-11-22_l11_reading_1500.json "
        f"shows remaining {out['remaining']} of {out['dead_names']}. "
        f"delisted_pull pid {out['daemon_pid']}, phase {out['phase']}, cycles "
        f"{out['cycles']}, remaining {out['remaining']}. Unchanged since the "
        f"13:00 note. The vendor serves nothing earlier. Blocked on the "
        f"vendor's start date."
    )
    text = open(BACKLOG).read()
    if note.strip() in text:
        print(path)
        print("note already present")
        return
    line = next(ln for ln in text.splitlines() if ln.startswith("- L11. "))
    if ANCHOR not in line:
        raise SystemExit("anchor missing from the L11 line")
    updated = line.replace(ANCHOR, ANCHOR + note, 1)
    open(BACKLOG, "w").write(text.replace(line, updated, 1))
    print(path)
    print("noted")


if __name__ == "__main__":
    main()
