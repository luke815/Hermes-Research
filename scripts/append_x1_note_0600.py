"""Record this run's reading of X1 on its backlog line.

The status line comes from ops/sweep_status and the sweep state from
ops/sweep_xs_heartbeat. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
STATUS = os.path.join(ROOT, "ops", "sweep_status")
HEARTBEAT = os.path.join(ROOT, "ops", "sweep_xs_heartbeat")
ANCHOR = "Unblocks when ops/sweep_status shows cells per hour above 5,000."


def main():
    line_text = open(STATUS).read().strip()
    beat = json.load(open(HEARTBEAT))
    text = open(PATH).read()
    marker = "Rechecked 2026-11-21 06:00 UTC: ops/sweep_status reads"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- X1. "))
    if ANCHOR not in line:
        raise SystemExit("anchor missing from the X1 line")
    rate = int(line_text.split("cells per hour", 1)[1].split(",")[0].strip())
    if rate > 5000:
        raise SystemExit("the rate cleared the bar; this note is the blocked reading")
    note = (
        " Rechecked 2026-11-21 06:00 UTC: ops/sweep_status reads '"
        f"{line_text}'. sweep_xs pid {beat['pid']}, alive, phase {beat['phase']}, "
        f"cycles {beat['cycles']}, remaining {beat['remaining']}. "
        "Blocked on the range columns reaching the panel the sweep reads. "
        "Unblocks when ops/sweep_status shows cells per hour above 5,000."
    )
    updated = line.replace(ANCHOR, ANCHOR + note, 1)
    open(PATH, "w").write(text.replace(line, updated, 1))
    print("appended", rate)


if __name__ == "__main__":
    main()
