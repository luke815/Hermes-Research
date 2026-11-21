"""Record the 13:00 reading of X1 on its backlog line.

The numbers come from results/2026-11-21_x1_status.json and
results/2026-11-21_x1_range_1300.json, both written by their scripts, and
from the sweep_xs heartbeat. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
STATUS = os.path.join(ROOT, "results", "2026-11-21_x1_status.json")
RANGE = os.path.join(ROOT, "results", "2026-11-21_x1_range_1300.json")
HEARTBEAT = os.path.join(ROOT, "ops", "sweep_xs_heartbeat")


def main():
    status = json.load(open(STATUS))
    span = json.load(open(RANGE))
    beat = json.load(open(HEARTBEAT))
    text = open(PATH).read()
    marker = "Rechecked 2026-11-21 13:00 UTC: results/2026-11-21_x1_status.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- X1. "))
    rate = status["status_line"].split("cells per hour", 1)[1].strip()
    note = (
        " Rechecked 2026-11-21 13:00 UTC: results/2026-11-21_x1_status.json "
        f"shows cells per hour {rate}, names {status['sweep']['names']}, "
        f"{status['open_emittable']} emittable cells still open, "
        f"{status['open_market_level']} market-level and "
        f"{status['open_needs_range']} that need high and low. "
        "results/2026-11-21_x1_range_1300.json counts high and low on "
        f"{span['with_high_low_header']} of {span['files']} files, and "
        f"{span['with_a_value']} of those have a value. sweep_xs pid "
        f"{beat.get('pid')}, phase {beat.get('phase')}, cycles "
        f"{beat.get('cycles')}, remaining {beat.get('remaining')}. The range "
        "columns are a few days deep, so the cells that need them still do "
        "not score. Blocked on the range columns reaching the panel the "
        "sweep reads. Unblocks when ops/sweep_status shows cells per hour "
        "above 5,000."
    )
    open(PATH, "w").write(text.replace(line, line + note, 1))
    print("appended")


if __name__ == "__main__":
    main()
