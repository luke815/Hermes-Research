"""Record the Q5 reading on its backlog line.

The numbers come from results/2026-11-21_q5_crowded_shorts.json, written by
scripts/score_q5.py. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-21_q5_crowded_shorts.json")
ANCHOR = "Done when results/<date>_q5_crowded_shorts.json reports every member of the"


def main():
    reading = json.load(open(RESULT))
    text = open(PATH).read()
    marker = "Scored 2026-11-21: results/2026-11-21_q5_crowded_shorts.json"
    if marker in text:
        raise SystemExit("note already present")
    lines = text.splitlines(keepends=True)
    index = next(i for i, ln in enumerate(lines) if ANCHOR in ln)
    counts = {}
    for cell in reading["cells"]:
        counts[cell["verdict"]] = counts.get(cell["verdict"], 0) + 1
    note = (
        " Scored 2026-11-21: results/2026-11-21_q5_crowded_shorts.json reports "
        f"all {len(reading['members'])} members at both horizons with the "
        "excess and the episode count per period. Pre-registration "
        f"{reading['prereg_commit'][:12]} precedes the scoring commit. "
        f"{reading['dropped_rescales']} names with a rescale-sized daily move "
        f"were dropped, leaving {reading['alt_names']} alts. "
        f"{counts.get('kept', 0)} cells kept, {counts.get('rejected', 0)} "
        f"rejected, {counts.get('insufficient', 0)} insufficient. The Binance "
        "BTC funding and the open-interest-weighted BTC funding keep a "
        "positive excess in validation and test at 3 and 5 days. ETH flips "
        "sign. The 30-day z-score has 16 episodes across train and validation "
        "against a bar of 20. The alt pool's BTC-subtracted excess is "
        "positive in validation and negative in test. Verdict 2026-11-21: "
        "rejected. The family does not keep one sign across BTC, ETH and the "
        "alt pool."
    )
    lines[index] = lines[index].rstrip("\n") + note + "\n"
    open(PATH, "w").write("".join(lines))
    print(f"appended {counts}")


if __name__ == "__main__":
    main()
