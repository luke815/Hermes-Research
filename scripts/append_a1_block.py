"""Append the A1 block note to the backlog line, citing the results file.

The count comes from results/2026-11-19_a1_block.json, which
scripts/a1_block_note.py wrote. This script only copies that number onto the
backlog line so the next run sees the reason.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-19_a1_block.json")

ANCHOR = "and the panel swap waits on those."
NOTE = (" Blocked 2026-11-19: the funding_sum daemon is walking the live names "
        "and a research run does not pull. results/2026-11-19_a1_block.json "
        "counts {missing} of {live} live names with no sum file "
        "({bybit} Bybit, {okx} OKX). Unblocks when that count is 0 and "
        "a1_rewrite.py swaps data/panel_xs_sum over data/panel_xs through data_guard.")


def main():
    payload = json.load(open(RESULT))
    note = NOTE.format(missing=payload["missing_sum_file"], live=payload["live_names"],
                       bybit=payload["missing_per_venue"].get("bybit", 0),
                       okx=payload["missing_per_venue"].get("okx", 0))
    text = open(BACKLOG).read()
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    if "Blocked 2026-11-19" in text.split("- A5.")[0]:
        raise SystemExit("block note already present")
    open(BACKLOG, "w").write(text.replace(ANCHOR, ANCHOR + note, 1))
    print("backlog updated", os.path.getsize(BACKLOG))


if __name__ == "__main__":
    main()
