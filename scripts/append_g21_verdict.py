"""Record the G21 verdict on its backlog line.

The numbers come from results/2026-11-22_g21_bb_pct.json, written by
scripts/score_g21.py. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-22_g21_bb_pct.json")


def main():
    reading = json.load(open(RESULT))
    text = open(PATH).read()
    marker = f"Scored {reading['provenance']['written_at'][:10]}: results/2026-11-22_g21_bb_pct.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- G21. "))
    periods = reading["periods"]
    test = periods["test"]
    validation = periods["validation"]
    note = (
        f" Scored {reading['provenance']['written_at'][:10]}: "
        f"results/2026-11-22_g21_bb_pct.json, written by scripts/score_g21.py. "
        f"{reading['names']} names, panel end {reading['panel_end']}, "
        f"lookahead passed. Train spread {periods['train']['spread_independent']} "
        f"on {periods['train']['n_independent']} independent dates. Validation "
        f"spread {validation['spread_independent']} on "
        f"{validation['n_independent']} independent dates, t {validation['t']}. "
        f"Test spread {test['spread_independent']} on {test['n_independent']} "
        f"independent dates, t {test['t']}. The test period holds "
        f"{test['n_independent']} independent dates against a bar of 40, and "
        f"the test spread flips the train sign. Verdict "
        f"{reading['provenance']['written_at'][:10]}: {reading['verdict']}.")
    if not line.endswith("data/panel_xs_laevitas."):
        raise SystemExit("the G21 line no longer ends where the note expects")
    open(PATH, "w").write(text.replace(line, line + note, 1))
    print("appended", reading["verdict"], test["n_independent"])


if __name__ == "__main__":
    main()
