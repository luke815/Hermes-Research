"""Record this run's reading of X1 on its backlog line.

The numbers come from results/2026-11-21_x1_status.json, written by
scripts/x1_status.py, and the range count is taken by reading every file in
data/panel_xs_laevitas. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-21_x1_status.json")
PANEL = os.path.join(ROOT, "data", "panel_xs_laevitas")
ANCHOR = "Unblocks when ops/sweep_status shows cells per hour above 5,000."


def range_count():
    files = [n for n in os.listdir(PANEL) if n.endswith(".csv")]
    with_header = 0
    with_value = 0
    for name in files:
        with open(os.path.join(PANEL, name)) as handle:
            header = handle.readline().rstrip("\n").split(",")
            if "high" not in header or "low" not in header:
                continue
            with_header += 1
            at = header.index("high")
            for line in handle:
                row = line.rstrip("\n").split(",")
                if at < len(row) and row[at] not in ("", "nan", "NaN"):
                    with_value += 1
                    break
    return len(files), with_header, with_value


def main():
    status = json.load(open(RESULT))
    files, with_header, with_value = range_count()
    text = open(PATH).read()
    marker = "Rechecked 2026-11-21 09:00 UTC: results/2026-11-21_x1_status.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- X1. "))
    at = line.rfind(ANCHOR)
    if at < 0:
        raise SystemExit("anchor missing from the X1 line")
    beat = status["sweep"]
    rate = status["status_line"].split("cells per hour", 1)[1].strip()
    note = (
        " Rechecked 2026-11-21 09:00 UTC: results/2026-11-21_x1_status.json "
        f"shows cells per hour {rate}, names {beat['names']}, "
        f"{status['open_emittable']} emittable cells still open, "
        f"{status['open_market_level']} market-level and "
        f"{status['open_needs_range']} that need high and low. "
        f"data/panel_xs_laevitas has high and low on {with_header} of "
        f"{files} files, and {with_value} of those have a value. "
        f"sweep_xs pid {beat['pid']}, phase {beat['phase']}, cycles "
        f"{beat['cycles']}, remaining {beat['remaining']}. The range columns "
        "are a few days deep, so the cells that need them still do not score. "
        "Blocked on the range columns reaching the panel the sweep reads. "
        "Unblocks when ops/sweep_status shows cells per hour above 5,000."
    )
    updated = line[:at] + ANCHOR + note + line[at + len(ANCHOR):]
    open(PATH, "w").write(text.replace(line, updated, 1))
    print("appended", files, with_header, with_value)


if __name__ == "__main__":
    main()
