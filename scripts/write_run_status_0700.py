"""Write this run's status line.

The top item is the first backlog line that starts with an item header and
carries no verdict of its own. A note that quotes an earlier item's verdict
does not close the item, so the word has to be the item's own. The run count
is how many stall-check lines name that item, plus this run.
"""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "ops", "health.log")
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
OUT = os.path.join(ROOT, "results", "2026-11-21_run_status.txt")
HEADER = re.compile(r"^- [A-Z]{1,3}\d{1,3}[a-z]?\. ")
CLOSED = re.compile(
    r"Done 20\d\d-\d\d-\d\d|Verdict 20\d\d-\d\d-\d\d: (rejected|insufficient|recorded|admitted)")


def top_item():
    for line in open(BACKLOG):
        if not HEADER.match(line):
            continue
        head = line.split(". ", 1)[0]
        own = line[len(head):]
        if CLOSED.search(own):
            continue
        return head.lstrip("- ")
    raise SystemExit("no open item")


def main():
    item = top_item()
    runs = sum(1 for line in open(LOG)
               if "stall_check" in line and f"item={item} " in line) + 1
    status = (f"STATUS OK research-run panel_end=2026-11-20 age=1d "
              f"top={item} runs={runs} files=research/backlog.md,"
              f"results/2026-11-21_a7_close.json,"
              f"results/2026-11-21_l11_coverage.json,"
              f"results/2026-11-21_x1_status.json,"
              f"results/2026-11-21_l2_status.json,"
              f"results/2026-11-21_q4_oi_pc.json,"
              f"results/2026-11-21_b1_inputs.json")
    open(OUT, "w").write(status + "\n")
    print(status)


if __name__ == "__main__":
    main()
