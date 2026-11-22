"""Record the G28 verdict on its backlog line.

The numbers come from results/2026-11-22_g28_obv.json, written by
scripts/score_g28.py. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-22_g28_obv.json")
ANCHOR = "a price change after day t leaves the signal at t unchanged."


def main():
    result = json.load(open(RESULT))
    text = open(PATH).read()
    marker = "Scored 2026-11-22: results/2026-11-22_g28_obv.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines()
                if ln.startswith("2. xs_obv_xs_rank_below_10_ret_10. "))
    if ANCHOR not in line:
        raise SystemExit("anchor missing from the G28 line")
    periods = result["periods"]
    train = periods["train"]
    validation = periods["validation"]
    test = periods["test"]
    note = (
        " Scored 2026-11-22: results/2026-11-22_g28_obv.json, written by "
        "scripts/score_g28.py. "
        f"{result['names']} names, panel end {result['panel_end']}, lookahead "
        f"{'passed' if result['lookahead_holds'] else 'FAILED'}. "
        f"Train spread {train['spread_independent']} on "
        f"{train['n_independent']} independent dates, t {train['t']}. "
        f"Validation spread {validation['spread_independent']} on "
        f"{validation['n_independent']} independent dates, t {validation['t']}. "
        f"Test spread {test['spread_independent']} on "
        f"{test['n_independent']} independent dates, t {test['t']}. "
        f"The test period holds {test['n_independent']} independent dates "
        f"against a bar of 40, and the test spread flips the train sign. "
        f"Verdict 2026-11-22: {result['verdict']}."
    )
    updated = "- G28. " + line[len("2. "):].rstrip("\n") + note + "\n"
    open(PATH, "w").write(text.replace(line, updated, 1))
    print("appended")


if __name__ == "__main__":
    main()
