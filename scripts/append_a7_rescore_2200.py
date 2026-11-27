"""Append the 22:00 rescore note to the A7 line.

The reading is results/2026-11-21_a7_block_2200.json, written by
scripts/record_a7_block_2200.py. The rescore started after the scale fix
and was stopped before it wrote a results file: the first attempt reached
file 3000 of 5538 in 450 seconds and was killed at the 600 second limit,
and the second was stopped after 3 minutes with an empty log. A7(3) stays
blocked on the five missing derivs_summary files.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
MARKER = "The rescore did not finish this run."


def main():
    text = open(BACKLOG).read()
    if MARKER in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- A7. "))
    anchor = "A research run does not pull. "
    at = line.find(anchor)
    if at < 0 or not line.startswith("Rechecked 2026-11-21 22:00 UTC"):
        raise SystemExit("22:00 note is not at the head of the A7 line")
    note = (
        "The rescore did not finish this run. scripts/score_a7_reversal.py "
        "was started after the swap and reached file 3000 of 5538 in 450 "
        "seconds before the 600 second limit killed it, and a second start "
        "was stopped after 3 minutes with an empty log. No "
        "results/2026-11-21_a7_reversal.json was written. ")
    updated = line[:at + len(anchor)] + note + line[at + len(anchor):]
    open(BACKLOG, "w").write(text.replace(line, updated, 1))
    print("noted")


if __name__ == "__main__":
    main()
