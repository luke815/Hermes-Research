"""Record this run's reading of X1 on its backlog line.

The numbers come from results/2026-11-20_x1_status.json, written by
scripts/x1_status.py. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-20_x1_status.json")
ANCHOR = "Blocked on the range columns reaching the panel the sweep reads."


def main():
    reading = json.load(open(RESULT))
    text = open(PATH).read()
    marker = "Rechecked 2026-11-20 23:00 UTC: results/2026-11-20_x1_status.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- X1. "))
    if ANCHOR not in line:
        raise SystemExit("anchor missing from the X1 line")
    sweep = reading["sweep"]
    laev = reading["laevitas_range"]
    old = reading["old_panel_range"]
    note = (
        " Rechecked 2026-11-20 23:00 UTC: results/2026-11-20_x1_status.json "
        f"shows cells per hour {reading['status_line'].rsplit('cells per hour ', 1)[-1]}, "
        f"names {sweep.get('names')}, {reading['open_emittable']} emittable cells still open, "
        f"{reading['open_market_level']} market-level and {reading['open_needs_range']} "
        f"that need high and low. data/panel_xs_laevitas has high and low on "
        f"{laev['with_high_low']} of {laev['files']} files. The high_low daemon writes "
        f"data/panel_xs, where {old['with_high_low']} of {old['files']} files carry both "
        f"columns, and the sweep does not read that directory. sweep_xs pid {sweep.get('pid')}, "
        f"alive, phase {sweep.get('phase')}, cycles {sweep.get('cycles')}, remaining "
        f"{sweep.get('remaining')}. The Laevitas perpetual store has no high or low field, "
        "so the columns are not on disk to copy. Blocked on the range columns reaching "
        "the panel the sweep reads. Unblocks when ops/sweep_status shows cells per hour above 5,000."
    )
    updated = line.replace(ANCHOR, ANCHOR + note, 1)
    open(PATH, "w").write(text.replace(line, updated, 1))
    print("appended")


if __name__ == "__main__":
    main()
