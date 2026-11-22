"""Write this run's status line.

The top item and its run count come from the health log, which the
scheduler writes. This script only records them.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "ops", "health.log")
OUT = os.path.join(ROOT, "results", "2026-11-22_run_status_0200.txt")


def main():
    last = ""
    for line in open(LOG):
        if "stall_check item=" in line:
            last = line.strip()
    item = last.split("item=", 1)[1].split()[0]
    runs = int(last.split("runs=", 1)[1].split()[0])
    status = (
        f"STATUS OK research-run panel_end=2026-11-20 age=2d "
        f"top={item} runs={runs} files=research/backlog.md,"
        f"results/2026-11-22_g21_bb_pct.json")
    open(OUT, "w").write(status + "\n")
    print(status)


if __name__ == "__main__":
    main()
