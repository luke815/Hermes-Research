"""Record the 15:00 reading of X1.

The rate comes from ops/sweep_status. The open-cell counts come from
results/2026-11-22_x1_status.json, written by scripts/x1_status.py in this
run. The range depth is read from both panels. This script records the
reading. It does not score and it does not pull.
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
PRIOR = os.path.join(ROOT, "results", "2026-11-22_x1_status.json")
PANEL = os.path.join(ROOT, "data", "panel_xs_laevitas")
DONOR = os.path.join(ROOT, "data", "panel_xs")
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
SLOT = "2026-11-22 15:00"


def _span(directory, limit):
    files = [name for name in os.listdir(directory) if name.endswith(".csv")]
    with_header = with_value = deep = 0
    for name in files[:limit]:
        path = os.path.join(directory, name)
        header = open(path).readline().rstrip("\n").split(",")
        if "high" not in header or "low" not in header:
            continue
        with_header += 1
        at = header.index("high")
        filled = 0
        for line in open(path):
            parts = line.split(",")
            if len(parts) > at and parts[at] not in ("", "high", "nan", "None"):
                filled += 1
        if filled:
            with_value += 1
        if filled >= 30:
            deep += 1
    return {"files": len(files), "checked": min(limit, len(files)),
            "with_header": with_header, "with_value": with_value,
            "deep_30": deep}


def main():
    line = open(STATUS).read().strip()
    rate = int(line.split("cells per hour", 1)[1].split(",")[0].strip())
    beat = json.load(open(HEARTBEAT))
    high_low = json.load(open(HIGH_LOW))
    prior = json.load(open(PRIOR))
    panel = _span(PANEL, 800)
    donor = _span(DONOR, 200)
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
        "panel_checked": panel,
        "donor_checked": donor,
        "high_low_pid": high_low.get("pid"),
        "high_low_phase": high_low.get("phase"),
        "high_low_cycles": high_low.get("cycles"),
        "high_low_remaining": high_low.get("remaining"),
        "high_low_version": high_low.get("version"),
        "blocked": "range columns on the panel the sweep reads are a few days deep",
        "unblocks": "ops/sweep_status shows cells per hour above 5,000",
    }
    path = write_result("x1_block_1500", payload, inputs=[
        "ops/sweep_status", "ops/sweep_xs_heartbeat", "ops/high_low_heartbeat",
        "results/2026-11-22_x1_status.json", "data/panel_xs_laevitas",
        "data/panel_xs"])
    print(path)
    if rate > 5000:
        raise SystemExit("the rate cleared the bar; not marking blocked")
    note = (
        f" Rechecked {SLOT} UTC: results/2026-11-22_x1_block_1500.json shows "
        f"cells per hour {rate}, names {payload['names']}, "
        f"{payload['open_emittable']} emittable cells still open, "
        f"{payload['open_market_level']} market-level and "
        f"{payload['open_needs_range']} that need high and low. "
        f"results/2026-11-22_x1_status.json counted the open cells. "
        f"Of the first {panel['checked']} files in data/panel_xs_laevitas, "
        f"{panel['with_header']} carry a high and low header, "
        f"{panel['with_value']} have a value and {panel['deep_30']} have 30 "
        f"or more values. Of the first {donor['checked']} files in "
        f"data/panel_xs, {donor['with_value']} have a value and "
        f"{donor['deep_30']} have 30 or more. sweep_xs pid "
        f"{payload['sweep_pid']}, phase {payload['sweep_phase']}, cycles "
        f"{payload['sweep_cycles']}, remaining {payload['sweep_remaining']}. "
        f"high_low pid {payload['high_low_pid']}, version "
        f"{payload['high_low_version']}, phase {payload['high_low_phase']}, "
        f"cycles {payload['high_low_cycles']}, remaining "
        f"{payload['high_low_remaining']}. The range columns are a few days "
        f"deep, so the cells that need them still do not score. Blocked on "
        f"the range columns reaching the panel the sweep reads. Unblocks "
        f"when ops/sweep_status shows cells per hour above 5,000."
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
