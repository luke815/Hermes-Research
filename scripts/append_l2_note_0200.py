"""Record this run's reading of L2 on its backlog line.

The numbers come from results/2026-11-21_l2_status.json, written by
scripts/l2_status.py. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-21_l2_status.json")
ANCHOR = "Unblocks when that file shows both families closed, option missing 0 and liquidation missing 0."


def main():
    reading = json.load(open(RESULT))
    text = open(PATH).read()
    marker = "Rechecked 2026-11-21 02:00 UTC: results/2026-11-21_l2_status.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- L2. "))
    if ANCHOR not in line:
        raise SystemExit("anchor missing from the L2 line")
    options = reading["options"]
    liquidations = reading["liquidations"]
    puller = reading["puller"]
    note = (
        " Rechecked 2026-11-21 02:00 UTC: results/2026-11-21_l2_status.json "
        f"shows perpetual_closed {reading['perpetual_closed']} and "
        f"future_closed {reading['future_closed']}, maturities walked "
        f"{reading['maturities_walked']} of {reading['maturities_listed']}, "
        f"option files {options['files']} of {options['listed']} with "
        f"{options['missing']} missing, liquidation files "
        f"{liquidations['files']} of {liquidations['listed']} with "
        f"{liquidations['missing']} missing. laevitas_pull pid "
        f"{puller['pid']}, alive, phase {puller['phase']}, cycles "
        f"{puller['cycles']}, remaining {puller['remaining']}. The puller "
        "was refetching one name whose vendor history stops at 2026-11-17; "
        "a refetch that reaches no later bar now closes that name for the "
        "day, and remaining fell from 4856. Blocked on the pull. Unblocks "
        "when that file shows both families closed, option missing 0 and "
        "liquidation missing 0."
    )
    updated = line.replace(ANCHOR, ANCHOR + note, 1)
    open(PATH, "w").write(text.replace(line, updated, 1))
    print("appended")


if __name__ == "__main__":
    main()
