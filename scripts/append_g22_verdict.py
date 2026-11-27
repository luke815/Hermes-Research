"""Record the G22 verdict on its backlog line.

The numbers come from results/2026-11-22_g22_bb_width.json, written by
scripts/score_g22.py. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-22_g22_bb_width.json")


def main():
    reading = json.load(open(RESULT))
    text = open(PATH).read()
    marker = "results/2026-11-22_g22_bb_width.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- G22. "))
    periods = reading["periods"]
    test = periods["test"]
    validation = periods["validation"]
    note = (
        f" Scored {reading['provenance']['written_at'][:10]}: "
        f"results/2026-11-22_g22_bb_width.json, written by scripts/score_g22.py. "
        f"{reading['names']} names, panel end {reading['panel_end']}, "
        f"lookahead passed. Train spread {periods['train']['spread_independent']} "
        f"on {periods['train']['n_independent']} independent dates, t "
        f"{periods['train']['t']}. Validation spread "
        f"{validation['spread_independent']} on {validation['n_independent']} "
        f"independent dates, t {validation['t']}. Test spread "
        f"{test['spread_independent']} on {test['n_independent']} independent "
        f"dates, t {test['t']}. Both held-out periods flip the train sign. "
        f"rel_1 equals ret_1 inside a same-day rank, and the spread is that one. "
        f"Verdict {reading['provenance']['written_at'][:10]}: {reading['verdict']}.")
    if not line.endswith("data/panel_xs_laevitas."):
        raise SystemExit("the G22 line no longer ends where the note expects")
    open(PATH, "w").write(text.replace(line, line + note, 1))
    print("appended", reading["verdict"], validation["n_independent"])


if __name__ == "__main__":
    main()
