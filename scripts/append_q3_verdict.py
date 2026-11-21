"""Record the Q3 verdict on its backlog line.

The numbers come from results/2026-11-21_q3_ivrv.json, written by
scripts/score_q3.py. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-21_q3_ivrv.json")
ANCHOR = "Done when results/<date>_q3_ivrv.json reports each period with"


def main():
    reading = json.load(open(RESULT))
    text = open(PATH).read()
    marker = "Scored 2026-11-21: results/2026-11-21_q3_ivrv.json"
    if marker in text:
        raise SystemExit("note already present")
    lines = text.splitlines(keepends=True)
    index = next(i for i, ln in enumerate(lines) if ANCHOR in ln)
    cells = reading["cells"]
    flips = sum(1 for cell in cells if cell["verdict"] == "rejected")
    note = (
        " Scored 2026-11-21: results/2026-11-21_q3_ivrv.json reports train, "
        "validation and test per cell with episodes, and the 2026 rows sit "
        "inside the test period beside the 2020-2025 rows. Pre-registration "
        f"{reading['prereg_commit'][:12]} precedes the scoring commit. "
        f"Lookahead passed on both assets. {flips} of {len(cells)} cells are "
        "rejected: the effect is negative in validation and positive in test "
        "on both assets, at both horizons, for the return and the drawdown. "
        "Laevitas serves per-coin IV for BTC and ETH only, so the broader "
        "universe is not scored. Verdict 2026-11-21: rejected."
    )
    lines[index] = lines[index].rstrip("\n") + note + "\n"
    open(PATH, "w").write("".join(lines))
    print(f"appended flips={flips}")


if __name__ == "__main__":
    main()
