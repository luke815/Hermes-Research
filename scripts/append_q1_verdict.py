"""Record the Q1 reading on its backlog line.

The numbers come from results/2026-11-20_q1_lsr_drawdown.json, written by
scripts/score_q1.py. This script only records the reading. The verdict is
not a pass: the pooled sign flips and the validation episode count is below
the bar.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-20_q1_lsr_drawdown.json")
ANCHOR = "The pooled panel is not scored. Not a verdict."


def main():
    reading = json.load(open(RESULT))
    pooled = [cell for cell in reading["cells"] if cell["asset"] == "pooled"]
    if len(pooled) != 3:
        raise SystemExit(f"expected 3 pooled windows, got {len(pooled)}")
    window = pooled[0]
    episodes = window["episodes"]
    held = window["episodes"]["train"] + window["episodes"]["validation"]
    if held >= 20 and window["periods"]["validation"]["drawdown_effect"] < 0:
        raise SystemExit("the pooled window clears the bar; this note records the miss")
    text = open(PATH).read()
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    validation = window["periods"]["validation"]["drawdown_effect"]
    test = window["periods"]["test"]["drawdown_effect"]
    note = (
        " Scored 2026-11-20 14:11 UTC: results/2026-11-20_q1_lsr_drawdown.json "
        f"scores the pooled panel, {reading['pooled_names']} names, lookahead "
        f"passed, pre-registration {reading['prereg_commit'][:10]}. The pooled "
        f"10-day window has {episodes['validation']} validation episode against "
        f"a bar of 20, and its drawdown effect is {validation} in validation "
        f"and {test} in test, so the sign flips. The 20-day and 30-day windows "
        "flip the same way. Not a verdict."
    )
    open(PATH, "w").write(text.replace(ANCHOR, note, 1))
    print("appended")


if __name__ == "__main__":
    main()
