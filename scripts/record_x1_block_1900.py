"""Record the 19:00 reading of what blocks X1.

The clause needs the sweep status line to show cells per hour above
5,000. The sweep reports nothing left to score while the work list still
has emittable cells open, and those cells need high and low. This reads
the status file, the heartbeat and the panel, writes the counts through
write_result, and appends the block note. It does not score and does
not pull.
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs_laevitas")
STATUS = os.path.join(ROOT, "ops", "sweep_status")
HEARTBEAT = os.path.join(ROOT, "ops", "sweep_xs_heartbeat")
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
PRIOR = os.path.join(ROOT, "results", "2026-11-21_x1_status.json")


def range_span():
    """How many panel files carry high and low, and how many have a value."""
    files = [name for name in os.listdir(PANEL) if name.endswith(".csv")]
    with_header = with_value = 0
    for name in files:
        path = os.path.join(PANEL, name)
        header = open(path).readline().rstrip("\n").split(",")
        if "high" not in header or "low" not in header:
            continue
        with_header += 1
        at = header.index("high")
        for line in open(path):
            parts = line.split(",")
            if len(parts) > at and parts[at] not in ("", "high", "nan", "None"):
                with_value += 1
                break
    return {"files": len(files), "with_header": with_header, "with_value": with_value}


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    line = open(STATUS).read().strip()
    beat = json.loads(open(HEARTBEAT).read())
    prior = json.loads(open(PRIOR).read())
    span = range_span()
    rate = int(line.split("cells per hour", 1)[1].split(",")[0].strip())
    payload = {
        "item": "X1",
        "today": today,
        "slot": "19:00",
        "status_line": line,
        "cells_per_hour": rate,
        "cells_per_hour_above_5000": rate > 5000,
        "open_emittable": prior["open_emittable"],
        "open_market_level": prior["open_market_level"],
        "open_needs_range": prior["open_needs_range"],
        "panel_files": span["files"],
        "range_header": span["with_header"],
        "range_with_value": span["with_value"],
        "sweep_pid": beat.get("pid"),
        "sweep_phase": beat.get("phase"),
        "sweep_cycles": beat.get("cycles"),
        "sweep_remaining": beat.get("remaining"),
    }
    path = write_result("x1_block_1900", payload, inputs=[
        "ops/sweep_status", "ops/sweep_xs_heartbeat",
        "results/2026-11-21_x1_status.json", "data/panel_xs_laevitas"])
    print(path)
    print(json.dumps({k: payload[k] for k in (
        "cells_per_hour", "open_emittable", "range_header",
        "range_with_value", "sweep_remaining")}))
    if rate > 5000:
        raise SystemExit("the rate cleared the bar; not marking blocked")
    text = open(BACKLOG).read()
    marker = f"Rechecked {today} 19:00 UTC: results/{today}_x1_block_1900.json"
    if marker in text:
        raise SystemExit("note already present")
    item = next(ln for ln in text.splitlines() if ln.startswith("- X1. "))
    anchor = "Unblocks when ops/sweep_status shows cells per hour above 5,000."
    if item.count(anchor) < 1:
        raise SystemExit("anchor missing")
    note = (
        f" Rechecked {today} 19:00 UTC: results/{today}_x1_block_1900.json "
        f"shows cells per hour {rate}, names {beat.get('names')}, "
        f"{prior['open_emittable']} emittable cells still open, "
        f"{prior['open_market_level']} market-level and "
        f"{prior['open_needs_range']} that need high and low. "
        f"results/{today}_x1_status.json counted the open cells. "
        f"data/panel_xs_laevitas has high and low on {span['with_header']} of "
        f"{span['files']} files, and {span['with_value']} of those have a "
        f"value. sweep_xs pid {beat.get('pid')}, phase {beat.get('phase')}, "
        f"cycles {beat.get('cycles')}, remaining {beat.get('remaining')}. "
        f"The range columns are a few days deep, so the cells that need them "
        f"still do not score. Blocked on the range columns reaching the panel "
        f"the sweep reads. {anchor}")
    updated = item.replace(anchor, note, 1)
    open(BACKLOG, "w").write(text.replace(item, updated, 1))
    print("noted")


if __name__ == "__main__":
    main()
