"""Record the Q6 reading on its backlog line.

The numbers come from results/2026-11-21_q6_xs_momentum.json, written by
scripts/score_q6.py. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-21_q6_xs_momentum.json")
ANCHOR = "Done when results/<date>_q6_xs_momentum.json shows both the"


def main():
    reading = json.load(open(RESULT))
    text = open(PATH).read()
    marker = "Scored 2026-11-21: results/2026-11-21_q6_xs_momentum.json"
    if marker in text:
        raise SystemExit("note already present")
    lines = text.splitlines(keepends=True)
    index = next(i for i, ln in enumerate(lines) if ANCHOR in ln)
    periods = reading["periods"]
    note = (
        " Scored 2026-11-21: results/2026-11-21_q6_xs_momentum.json shows the "
        "net spread and the rank IC per period. Pre-registration "
        f"{reading['prereg_commit'][:12]} precedes the scoring commit. "
        f"{reading['names']} names, {reading['dropped_rescales']} dropped as "
        f"rescales, {reading['rebalances']} weekly rebalances. Validation: "
        f"net {periods['validation']['net']} on "
        f"{periods['validation']['rebalances']} dates, IC "
        f"{periods['validation']['ic']}. Test: net {periods['test']['net']} "
        f"on {periods['test']['rebalances']} dates, IC {periods['test']['ic']}. "
        "The spread and the IC have opposite signs in both held-out periods. "
        "Verdict 2026-11-21: rejected."
    )
    lines[index] = lines[index].rstrip("\n") + note + "\n"
    open(PATH, "w").write("".join(lines))
    print("appended")


if __name__ == "__main__":
    main()
