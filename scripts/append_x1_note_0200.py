"""Record this run's reading of X1 on its backlog line.

The numbers come from results/2026-11-21_x1_status.json, written by
scripts/x1_status.py. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-21_x1_status.json")
ANCHOR = "Unblocks when ops/sweep_status shows cells per hour above 5,000."


def main():
    reading = json.load(open(RESULT))
    text = open(PATH).read()
    marker = "Rechecked 2026-11-21 02:00 UTC: results/2026-11-21_x1_status.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- X1. "))
    if ANCHOR not in line:
        raise SystemExit("anchor missing from the X1 line")
    sweep = reading["sweep"]
    note = (
        " Rechecked 2026-11-21 02:00 UTC: results/2026-11-21_x1_status.json "
        f"shows cells per hour 0, names {sweep['names']}, "
        f"{reading['open_emittable']} emittable cells still open, "
        f"{reading['open_market_level']} market-level and "
        f"{reading['open_needs_range']} that need high and low. "
        "data/panel_xs_laevitas has high and low on "
        f"{reading['laevitas_range']['with_high_low']} of "
        f"{reading['laevitas_range']['checked']} files checked. The high_low "
        "daemon writes data/panel_xs, where "
        f"{reading['old_panel_range']['with_high_low']} of "
        f"{reading['old_panel_range']['files']} files carry both columns, and "
        "the sweep does not read that directory. sweep_xs pid "
        f"{sweep['pid']}, alive, phase {sweep['phase']}, cycles "
        f"{sweep['cycles']}, remaining {sweep['remaining']}. Blocked on the "
        "range columns reaching the panel the sweep reads. Unblocks when "
        "ops/sweep_status shows cells per hour above 5,000."
    )
    updated = line.replace(ANCHOR, ANCHOR + note, 1)
    open(PATH, "w").write(text.replace(line, updated, 1))
    print("appended")


if __name__ == "__main__":
    main()
