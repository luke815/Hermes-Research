"""Record one recheck of X1.

The rate comes from ops/sweep_status. The open-cell counts come from
scripts/x1_status.py, run in this same process before the note is written.
The slot is today's UTC hour, read from the clock. This script records the
reading. It does not score and it does not pull.

Usage: python3 scripts/record_x1_reading.py
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402
from x1_status import main as status_main  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUS = os.path.join(ROOT, "ops", "sweep_status")
HEARTBEAT = os.path.join(ROOT, "ops", "sweep_xs_heartbeat")
HIGH_LOW = os.path.join(ROOT, "ops", "high_low_heartbeat")
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "Unblocks when ops/sweep_status shows cells per hour above 5,000."


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
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    hour = now.strftime("%H00")
    slot = now.strftime("%Y-%m-%d %H:00")
    status_main()
    today_status = json.load(open(os.path.join(
        ROOT, "results", f"{today}_x1_status.json")))
    line = open(STATUS).read().strip()
    rate = int(line.split("cells per hour", 1)[1].split(",")[0].strip())
    beat = json.load(open(HEARTBEAT))
    high_low = json.load(open(HIGH_LOW)) if os.path.exists(HIGH_LOW) else {}
    panel = _span(os.path.join(ROOT, "data", "panel_xs_laevitas"), 800)
    payload = {
        "item": "X1",
        "slot": slot,
        "status_line": line,
        "cells_per_hour": rate,
        "cells_per_hour_above_5000": rate > 5000,
        "names": beat.get("names"),
        "open_emittable": today_status["open_emittable"],
        "open_market_level": today_status["open_market_level"],
        "open_needs_range": today_status["open_needs_range"],
        "status_written_at": today_status["provenance"]["written_at"],
        "sweep_pid": beat.get("pid"),
        "sweep_phase": beat.get("phase"),
        "sweep_cycles": beat.get("cycles"),
        "sweep_remaining": beat.get("remaining"),
        "sweep_version": beat.get("version"),
        "panel_checked": panel,
        "high_low_pid": high_low.get("pid"),
        "high_low_phase": high_low.get("phase"),
        "high_low_cycles": high_low.get("cycles"),
        "high_low_remaining": high_low.get("remaining"),
        "blocked": rate <= 5000,
        "unblocks": (
            "ops/sweep_status shows cells per hour above 5,000 for one "
            "full hour"),
    }
    path = write_result(f"x1_block_{hour}", payload, inputs=[
        "ops/sweep_status", "ops/sweep_xs_heartbeat", "ops/high_low_heartbeat",
        f"results/{today}_x1_status.json", "data/panel_xs_laevitas"])
    print(path)
    if rate > 5000:
        raise SystemExit("the rate cleared the bar; not marking blocked")
    note = (
        f" Rechecked {slot} UTC: results/{today}_x1_block_{hour}.json shows "
        f"cells per hour {rate}, names {payload['names']}, "
        f"{payload['open_emittable']} emittable cells still open, "
        f"{payload['open_market_level']} market-level and "
        f"{payload['open_needs_range']} that need high and low. "
        f"results/{today}_x1_status.json, written "
        f"{payload['status_written_at']}, counted the open cells. "
        f"Of the first {panel['checked']} files in data/panel_xs_laevitas, "
        f"{panel['with_header']} carry a high and low header, "
        f"{panel['with_value']} have a value and {panel['deep_30']} have 30 "
        f"or more values. sweep_xs pid {payload['sweep_pid']}, version "
        f"{payload['sweep_version']}, phase {payload['sweep_phase']}, cycles "
        f"{payload['sweep_cycles']}, remaining {payload['sweep_remaining']}. "
        f"high_low pid {payload['high_low_pid']}, phase "
        f"{payload['high_low_phase']}, cycles {payload['high_low_cycles']}, "
        f"remaining {payload['high_low_remaining']}. The rate has not held "
        f"above 5,000 for one full hour. Blocked on the rate. {ANCHOR}"
    )
    text = open(BACKLOG).read()
    if note.strip() in text:
        print("note already present")
        return
    item = next(ln for ln in text.splitlines() if ln.startswith("- X1. "))
    if ANCHOR not in item:
        raise SystemExit("anchor missing")
    updated = item.replace(ANCHOR, ANCHOR + note, 1)
    open(BACKLOG, "w").write(text.replace(item, updated, 1))
    print("noted")


if __name__ == "__main__":
    main()
