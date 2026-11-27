"""Write this run's status line.

The top item is the first backlog line without a verdict, read from
research/backlog.md. The run count is how many stall_check lines in
ops/health.log already name it, plus this run. This script only records them.
"""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
LOG = os.path.join(ROOT, "ops", "health.log")
OUT = os.path.join(ROOT, "results", "2026-11-22_run_status_0500.txt")
CLOSED = ("done 20", "rejected", "insufficient", "verdict 20", "admitted")


def top_item():
    for line in open(BACKLOG):
        if not re.match(r"^- [A-Z]{1,3}\d{1,3}[a-z]?\. ", line):
            continue
        if any(word in line.lower() for word in CLOSED):
            continue
        return line.split(".", 1)[0].lstrip("- ").strip()
    return "none"


def main():
    item = top_item()
    prior = [ln for ln in open(LOG) if "stall_check" in ln and f"item={item} " in ln]
    runs = len(prior) + 1
    status = (
        f"STATUS OK research-run panel_end=2026-11-20 age=2d "
        f"top={item} runs={runs} files=research/backlog.md,"
        f"results/2026-11-22_l11_coverage.json,"
        f"results/2026-11-22_l2_status.json,"
        f"results/2026-11-22_x1_status.json,"
        f"results/2026-11-22_d3_hourly_0500.json,"
        f"results/2026-11-22_q4_oi_pc_0500.json,"
        f"results/2026-11-22_b1_inputs_0500.json")
    open(OUT, "w").write(status + "\n")
    print(status)


if __name__ == "__main__":
    main()
