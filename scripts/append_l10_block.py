"""Append the L10 block note, citing the results file written this run."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "Done when the 05:35 slot has refilled a real deleted day, which has not happened yet."
NOTE = (" Blocked 2026-11-19: the slot has never fired. results/2026-11-19_l10_slot.json lists six 05:35 cycles, each with an empty run, and no laevitas_refresh results file. A failed attempt used to close the slot for the day; scripts/scheduler.py now retries it, and the scheduler was restarted onto 677baef. Unblocks when the 05:35 slot writes results/<date>_laevitas_refresh.json with a refilled day, which the scheduler does, not a research run.")


def main():
    text = open(BACKLOG).read()
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    open(BACKLOG, "w").write(text.replace(ANCHOR, ANCHOR + NOTE, 1))
    print("backlog updated", os.path.getsize(BACKLOG))


if __name__ == "__main__":
    main()
