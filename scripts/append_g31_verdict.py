"""Record the G31 score on the line after the clause.

The numbers come from results/2026-11-23_g31_sma20.json, written by
scripts/score_g31.py. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-23_g31_sma20.json")
ANCHOR = "a price change after day t leaves the signal at t unchanged."


def main():
    result = json.load(open(RESULT))
    text = open(PATH).read()
    marker = "Scored 2026-11-23: results/2026-11-23_g31_sma20.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- G31. "))
    if ANCHOR not in line:
        raise SystemExit("anchor missing from the G31 line")
    periods = result["periods"]
    train = periods["train"]
    validation = periods["validation"]
    test = periods["test"]
    note = (
        "Scored 2026-11-23: results/2026-11-23_g31_sma20.json, written by "
        "scripts/score_g31.py. "
        f"{result['names']} names, panel end {result['panel_end']}, lookahead "
        f"{'passed' if result['lookahead_holds'] else 'FAILED'}. "
        f"Train spread {train['spread_independent']} on "
        f"{train['n_independent']} independent dates, t {train['t']}. "
        f"Validation spread {validation['spread_independent']} on "
        f"{validation['n_independent']} independent dates, t {validation['t']}. "
        f"Test spread {test['spread_independent']} on "
        f"{test['n_independent']} independent dates, t {test['t']}. "
        "The test spread flips the train sign. rel_1 equals ret_1 inside "
        "a same-day rank, and the spread is that one. "
        f"Verdict 2026-11-23: {result['verdict']}."
    )
    updated = line.rstrip() + "\n" + note + "\n"
    open(PATH, "w").write(text.replace(line, updated, 1))
    print("appended")


if __name__ == "__main__":
    main()
