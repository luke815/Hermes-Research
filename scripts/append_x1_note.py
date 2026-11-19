"""Append this run's reading of X1 to its backlog line."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "Not done: the status line has not yet shown cells per hour above 5,000 for one full hour."
NOTE = (" Rechecked 2026-11-19 13:30 UTC: the panel now holds 5,538 files after "
        "the L11 merge, and the sweep restarted onto it reports 234 names "
        "against 219 before. results/2026-11-19_x1_status.json shows cells per "
        "hour not above 5,000. The sweep's first cycle on the new universe "
        "refuses the write with a duplicate cell id, and that is what blocks "
        "the rate. sweep_xs pid 3166, version fd0b898, is rebuilding its cache.")


def main():
    text = open(PATH).read()
    if "results/2026-11-19_x1_status.json" in text:
        raise SystemExit("note already present")
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    open(PATH, "w").write(text.replace(ANCHOR, ANCHOR + NOTE, 1))
    print("appended")


if __name__ == "__main__":
    main()
