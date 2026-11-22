"""Record the G24 verdict on its backlog line.

The numbers come from results/2026-11-22_g24_roc_12.json, written by
scripts/score_g24.py. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-22_g24_roc_12.json")
ANCHOR = "Not yet scored. Cross-sectional, on data/panel_xs_laevitas."


def main():
    result = json.load(open(RESULT))
    text = open(PATH).read()
    marker = "Scored 2026-11-22: results/2026-11-22_g24_roc_12.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- G24. "))
    if ANCHOR not in line:
        raise SystemExit("anchor missing from the G24 line")
    periods = result["periods"]
    train = periods["train"]
    validation = periods["validation"]
    test = periods["test"]
    note = (
        " Scored 2026-11-22: results/2026-11-22_g24_roc_12.json, written by "
        "scripts/score_g24.py. "
        f"{result['names']} names, panel end {result['panel_end']}, lookahead "
        f"{'passed' if result['lookahead_holds'] else 'FAILED'}. "
        f"Train spread {train['spread_independent']} on "
        f"{train['n_independent']} independent dates, t {train['t']}. "
        f"Validation spread {validation['spread_independent']} on "
        f"{validation['n_independent']} independent dates, t {validation['t']}. "
        f"Test spread {test['spread_independent']} on "
        f"{test['n_independent']} independent dates, t {test['t']}. "
        "Both held-out periods flip the train sign. rel_1 equals ret_1 inside "
        f"a same-day rank, and the spread is that one. "
        f"Verdict 2026-11-22: {result['verdict']}."
    )
    updated = line.replace(ANCHOR, ANCHOR + note, 1)
    open(PATH, "w").write(text.replace(line, updated, 1))
    print("appended")


if __name__ == "__main__":
    main()
