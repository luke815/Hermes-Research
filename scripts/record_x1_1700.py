"""Record the 17:00 reading of X1.

The rate comes from ops/sweep_status. The walk comes from the high_low
heartbeat and the last line of its log. This script records the reading.
It does not score and it does not pull.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUS = os.path.join(ROOT, "ops", "sweep_status")
HEARTBEAT = os.path.join(ROOT, "ops", "sweep_xs_heartbeat")
HIGH_LOW = os.path.join(ROOT, "ops", "high_low_heartbeat")
LOG = os.path.join(ROOT, "ops", "logs", "high_low.log")
DEFERRED = os.path.join(ROOT, "ops", "high_low_deferred.json")
PRIOR = os.path.join(ROOT, "results", "2026-11-22_x1_status.json")
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
SLOT = "2026-11-22 17:00"


def main():
    line = open(STATUS).read().strip()
    rate = int(line.split("cells per hour", 1)[1].split(",")[0].strip())
    beat = json.load(open(HEARTBEAT))
    high_low = json.load(open(HIGH_LOW))
    prior = json.load(open(PRIOR))
    last = [row for row in open(LOG) if "cycle" in row][-1].strip()
    deferred = json.load(open(DEFERRED)) if os.path.exists(DEFERRED) else []
    payload = {
        "item": "X1",
        "slot": SLOT,
        "status_line": line,
        "cells_per_hour": rate,
        "cells_per_hour_above_5000": rate > 5000,
        "names": beat.get("names"),
        "open_emittable": prior["open_emittable"],
        "open_market_level": prior["open_market_level"],
        "open_needs_range": prior["open_needs_range"],
        "sweep_pid": beat.get("pid"),
        "sweep_phase": beat.get("phase"),
        "sweep_cycles": beat.get("cycles"),
        "sweep_remaining": beat.get("remaining"),
        "high_low_pid": high_low.get("pid"),
        "high_low_phase": high_low.get("phase"),
        "high_low_cycles": high_low.get("cycles"),
        "high_low_remaining": high_low.get("remaining"),
        "high_low_version": high_low.get("version"),
        "high_low_last_cycle": last,
        "deferred_count": len(deferred),
        "deferred_head": deferred[:3],
        "blocked": "cells per hour is 0; the range walk just moved past the 400",
        "unblocks": "ops/sweep_status shows cells per hour above 5,000",
    }
    path = write_result("x1_block_1700", payload, inputs=[
        "ops/sweep_status", "ops/sweep_xs_heartbeat", "ops/high_low_heartbeat",
        "ops/logs/high_low.log", "ops/high_low_deferred.json",
        "results/2026-11-22_x1_status.json"])
    print(path)
    if rate > 5000:
        raise SystemExit("the rate cleared the bar; not marking blocked")
    note = (
        f" Rechecked {SLOT} UTC: results/2026-11-22_x1_block_1700.json shows "
        f"cells per hour {rate}, names {payload['names']}, "
        f"{payload['open_emittable']} emittable cells still open, "
        f"{payload['open_market_level']} market-level and "
        f"{payload['open_needs_range']} that need high and low. "
        f"sweep_xs pid {payload['sweep_pid']}, phase {payload['sweep_phase']}, "
        f"cycles {payload['sweep_cycles']}, remaining "
        f"{payload['sweep_remaining']}. high_low pid {payload['high_low_pid']}, "
        f"version {payload['high_low_version']}, phase {payload['high_low_phase']}, "
        f"cycles {payload['high_low_cycles']}, remaining "
        f"{payload['high_low_remaining']}, deferred {payload['deferred_count']}. "
        f"The last cycle line is {last}. A 400 no longer pins the walk, and "
        f"the rate has not cleared 5,000. Blocked on the rate. Unblocks when "
        f"ops/sweep_status shows cells per hour above 5,000."
    )
    text = open(BACKLOG).read()
    if note.strip() in text:
        print("note already present")
        return
    item = next(ln for ln in text.splitlines() if ln.startswith("- X1. "))
    anchor = "Unblocks when ops/sweep_status shows cells per hour above 5,000."
    if anchor not in item:
        raise SystemExit("anchor missing")
    updated = item.replace(anchor, anchor + note, 1)
    open(BACKLOG, "w").write(text.replace(item, updated, 1))
    print("noted")


if __name__ == "__main__":
    main()
