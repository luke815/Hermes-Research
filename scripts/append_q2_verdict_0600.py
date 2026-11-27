"""Record the Q2 verdict on its backlog line.

The word comes from results/2026-11-21_q2_skew_no_vol.json, written by
scripts/score_q2.py. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-21_q2_skew_no_vol.json")
ANCHOR = "The claim was released. Not done."


def main():
    reading = json.load(open(RESULT))
    if reading["verdict"] != "insufficient":
        raise SystemExit(f"verdict is {reading['verdict']}; this note records insufficient")
    windows = {row["window"] for cell in reading["cells"] for row in cell["fresh"]}
    if windows != {"2019-03 to 2020-01", "2026"}:
        raise SystemExit(f"fresh windows are {windows}")
    text = open(PATH).read()
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    note = (
        f" Verdict 2026-11-21: {reading['verdict']}. "
        "results/2026-11-21_q2_skew_no_vol.json shows the two fresh windows "
        "separately, and its pre-registration commit precedes the scoring commit."
    )
    open(PATH, "w").write(text.replace(ANCHOR, ANCHOR + note, 1))
    print("appended", reading["verdict"])


if __name__ == "__main__":
    main()
