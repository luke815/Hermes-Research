"""Record the L6 close on its backlog line.

The closing line is the one done_check printed. The numbers come from the
results files the scoring scripts wrote.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
DONE = "Done 2026-11-20. done_check 2a7b3d6a38."
ANCHOR = "C5 and R1 to R6 each have a results file written by the script that scored them."


def main():
    positioning = json.load(open(os.path.join(ROOT, "results", "2026-11-20_l6_positioning.json")))
    c5 = json.load(open(os.path.join(ROOT, "results", "2026-11-20_l6_c5.json")))
    r4 = json.load(open(os.path.join(ROOT, "results", "2026-11-20_l6_r4.json")))
    text = open(PATH).read()
    if DONE in text:
        raise SystemExit("done line already present")
    count = text.count(ANCHOR)
    if count != 1:
        raise SystemExit(f"anchor count {count}")
    note = (
        f" {DONE} Positioning: results/2026-11-20_l6_positioning.json, "
        f"{positioning['cells']} cells, {positioning['usable']} usable, "
        f"{positioning['names']} names, verdict {positioning['verdict']}. "
        f"C5: results/2026-11-20_l6_c5.json, {c5['n_rows']} rows, verdict "
        f"{c5['verdict']}. R1 to R6: results/2026-11-20_l6_r1.json through "
        f"results/2026-11-20_l6_r6.json, R4 verdict {r4['verdict']}."
    )
    open(PATH, "w").write(text.replace(ANCHOR, ANCHOR + note, 1))
    print("appended")


if __name__ == "__main__":
    main()
