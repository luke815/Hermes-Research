"""Record this run's reading of A7 on its backlog line.

The numbers come from results/2026-11-20_a7_rest.json, written by
scripts/score_a7_rest.py. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-20_a7_rest.json")
ANCHOR = "A research run does not rewrite the panel. "


def main():
    reading = json.load(open(RESULT))
    cells = [c for c in reading["a7_2"] if not c.get("neighbour")]
    verdicts = {}
    for cell in cells:
        verdicts[cell["verdict"]] = verdicts.get(cell["verdict"], 0) + 1
    text = open(PATH).read()
    marker = "results/2026-11-20_a7_rest.json"
    if marker in text:
        raise SystemExit("note already present")
    if ANCHOR not in text:
        raise SystemExit("anchor missing")
    note = (
        "Rechecked 2026-11-20 11:00 UTC: results/2026-11-20_a7_rest.json scores "
        f"A7(2) and A7(4), lookahead passed, pre-registration {reading['prereg_commit'][:10]}. "
        f"A7(2) has {verdicts.get('rejected', 0)} rejected and "
        f"{verdicts.get('insufficient', 0)} insufficient of {len(cells)} cells, "
        "none kept on both assets. A7(4) is insufficient at 1 day and rejected "
        "at 3 days, on 2 names. A7(3) is blocked: data/laevitas/market has no "
        "derivs_summary for ADA, SOL, LINK, XRP or AVAX. A7(1) stays blocked on "
        "the bad close. "
    )
    open(PATH, "w").write(text.replace(ANCHOR, ANCHOR + note, 1))
    print("appended")


if __name__ == "__main__":
    main()
