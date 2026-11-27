"""Write this run's status line.

The top item is the first backlog line that starts with an item header and
carries no verdict of its own. The run count is how many stall-check lines
name that item, plus this run. The panel end date is read from the panel.
"""

import os
import re
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "ops", "health.log")
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
PANEL = os.path.join(ROOT, "data", "panel.csv")
OUT = os.path.join(ROOT, "results", "2026-11-22_run_status_1500.txt")
HEADER = re.compile(r"^- [A-Z]{1,3}\d{1,3}[a-z]?\. ")
CLOSED = re.compile(
    r"Done 20\d\d-\d\d-\d\d|Verdict 20\d\d-\d\d-\d\d: "
    r"(rejected|insufficient|recorded|admitted)")


def top_item():
    for line in open(BACKLOG):
        if not HEADER.match(line):
            continue
        head = line.split(". ", 1)[0]
        if CLOSED.search(line[len(head):]):
            continue
        return head.lstrip("- ")
    raise SystemExit("no open item")


def panel_end():
    last = None
    for line in open(PANEL):
        if line.strip():
            last = line
    return last.split(",")[0][:10]


def main():
    item = top_item()
    runs = sum(1 for line in open(LOG)
               if "stall_check" in line and f"item={item} " in line) + 1
    end = panel_end()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    age = (datetime.strptime(today, "%Y-%m-%d")
           - datetime.strptime(end, "%Y-%m-%d")).days
    status = (
        f"STATUS OK research-run panel_end={end} age={age}d "
        f"top={item} runs={runs} files=research/backlog.md,"
        f"results/2026-11-22_l11_coverage.json,"
        f"results/2026-11-22_l11_reading_1500.json,"
        f"results/2026-11-22_x1_status.json,"
        f"results/2026-11-22_x1_block_1500.json,"
        f"results/2026-11-22_l2_status.json,"
        f"results/2026-11-22_l2_reading_1500.json,"
        f"results/2026-11-22_d3_hourly_1500.json,"
        f"results/2026-11-22_q4_oi_pc_1500.json,"
        f"results/2026-11-22_b1_inputs_1500.json,"
        f"results/2026-11-22_b2_inputs_1500.json,"
        f"results/2026-11-22_b3_inputs_1500.json,"
        f"results/2026-11-22_b4_inputs_1500.json,"
        f"results/2026-11-22_b5_inputs_1500.json")
    open(OUT, "w").write(status + "\n")
    print(status)


if __name__ == "__main__":
    main()
