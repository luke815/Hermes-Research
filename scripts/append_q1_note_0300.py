"""Record this run's reading of Q1 on its backlog line.

The numbers come from results/2026-11-21_q1_lsr_drawdown.json, written by
scripts/record_q1_verdict.py, and from the hosted page check this run made.
This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-21_q1_lsr_drawdown.json")
ANCHOR = "Not a verdict."


def main():
    reading = json.load(open(RESULT))
    counts = {}
    for cell in reading["cells"]:
        counts[cell["verdict"]] = counts.get(cell["verdict"], 0) + 1
    text = open(PATH).read()
    marker = "Rechecked 2026-11-21 03:00 UTC: results/2026-11-21_q1_lsr_drawdown.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- Q1. "))
    if ANCHOR not in line:
        raise SystemExit("anchor missing from the Q1 line")
    note = (
        " Rechecked 2026-11-21 03:00 UTC: results/2026-11-21_q1_lsr_drawdown.json "
        f"carries 9 cells, {counts.get('kept', 0)} kept and "
        f"{counts.get('rejected', 0)} rejected, on {reading['pooled_names']} "
        "pooled names. The local page has the q1 key, source "
        "2026-11-21_q1_lsr_drawdown.json, as_of 2026-11-21T01:14:56Z, committed "
        "as dashboard 9153215 and pushed. The hosted page at "
        "https://luke815.github.io/Hermes-Dashboard-1/data.json still serves "
        "generated_at 2026-11-20T12:49:19Z and has no q1 key. Not done: the "
        "watch card is not on the page the clause names. Unblocks when that "
        "hosted file carries the q1 key."
    )
    updated = line.replace(ANCHOR, ANCHOR + note, 1)
    open(PATH, "w").write(text.replace(line, updated, 1))
    print("appended")


if __name__ == "__main__":
    main()
