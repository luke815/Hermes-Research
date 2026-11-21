"""Record this run's reading of X1 on its backlog line.

The numbers come from results/2026-11-21_x1_status.json, written by
scripts/x1_status.py, and from the panel file count printed by the copy. This
script only records the reading.
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
    marker = "Rechecked 2026-11-21 04:00 UTC: results/2026-11-21_x1_status.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- X1. "))
    if ANCHOR not in line:
        raise SystemExit("anchor missing from the X1 line")
    sweep = reading["sweep"]
    note = (
        " Rechecked 2026-11-21 04:00 UTC: results/2026-11-21_x1_status.json "
        f"shows cells per hour 0, names {sweep['names']}, "
        f"{reading['open_emittable']} emittable cells still open, "
        f"{reading['open_market_level']} market-level and "
        f"{reading['open_needs_range']} that need high and low. "
        "scripts/copy_range.py copied high and low from data/panel_xs and "
        "data_guard swapped the directory in, results/2026-11-21_swap_data__"
        "panel_xs_laevitas.json, previous kept as data/panel_xs_laevitas."
        "prev-20261121T042846Z. 776 of 5538 files now carry the columns, but "
        "the donor panel holds only a handful of dates per name, so the range "
        "measures stay unscoreable. scripts/sweep_xs.py now reads high and low "
        "when a file has them, tests/test_sweep_range.py, and the daemon was "
        "restarted onto that commit. The columns are not on disk in any depth. "
        "Blocked on the range columns reaching the panel the sweep reads. "
        "Unblocks when ops/sweep_status shows cells per hour above 5,000."
    )
    updated = line.replace(ANCHOR, ANCHOR + note, 1)
    open(PATH, "w").write(text.replace(line, updated, 1))
    print("appended")


if __name__ == "__main__":
    main()
