"""Record this run's Q1 reading on its backlog line.

The numbers come from results/2026-11-20_q1_lsr_drawdown.json, written by
scripts/score_q1.py. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-20_q1_lsr_drawdown.json")
ANCHOR = "- Q1. Long/short ratio top quintile"


def main():
    reading = json.load(open(RESULT))
    cells = reading["cells"]
    kept = sum(1 for c in cells if c["verdict"] == "kept")
    text = open(PATH).read()
    if "results/2026-11-20_q1_lsr_drawdown.json" in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith(ANCHOR))
    btc = next(c for c in cells if c["asset"] == "BTC" and c["window"] == 20)
    effect = btc["periods"]["validation"]["drawdown_effect"]
    note = (
        f" Read 2026-11-20 11:00 UTC: results/2026-11-20_q1_lsr_drawdown.json "
        f"scores BTC and ETH, {kept} of {len(cells)} windows kept their sign, "
        f"lookahead passed, pre-registration {reading['prereg_commit'][:10]}. "
        f"The BTC 20-day window's validation drawdown effect is {effect}. "
        "The pooled panel is not scored. Not a verdict."
    )
    open(PATH, "w").write(text.replace(line, line + note, 1))
    print("appended")


if __name__ == "__main__":
    main()
