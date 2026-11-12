"""Confirmation daemon. One eligible cell per cycle, no model involved.

Cross-sectional and event cells come first. A single-name cell is only tried
once every cross-sectional survivor on the leaderboard has been attempted.
A cell already in the confirmation record is skipped, and one whose expected
validation count is under 30 is never queued.

Usage: python3 scripts/confirm_daemon.py
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD = os.path.join(ROOT, "results", "sweeps", "leaderboard.json")
RECORD = os.path.join(ROOT, "results", "sweeps", "confirmations.json")


def attempted():
    if not os.path.exists(RECORD):
        return set()
    return {row["cell_id"] for row in json.load(open(RECORD))}


def eligible():
    board = json.load(open(BOARD)).get("leaderboard", [])
    done = attempted()
    fresh = [row for row in board if row["cell_id"] not in done
             and row.get("status") != "insufficient"]
    cross = [row for row in fresh if row.get("universe") == "pit_cross_section"
             or "pit_cross_section" in row["cell_id"]]
    events = [row for row in fresh if row["cell_id"].split("|")[4].startswith(("top_", "bottom_"))]
    single = [row for row in fresh if row not in cross and row not in events]
    return cross + events + single


def cycle(ctx):
    queue = eligible()
    if not queue:
        return {"cell": None, "remaining": 0}
    cell = queue[0]
    from regime_tester.indicators import META
    measure = cell["cell_id"].split("|")[0]
    family = META[measure][0] if measure in META else "trend"
    from regime_tester.confirm import confirm_cell
    record = confirm_cell(cell["cell_id"], family_n=cell.get("train_n", 1),
                          train_sign=1 if cell.get("train_score", 0) > 0 else -1)
    return {"cell": cell["cell_id"], "verdict": record["verdict"],
            "family": family, "remaining": len(queue) - 1}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from daemon_base import run_loop
    run_loop("confirm", interval_sec=300, cycle=cycle, align=False)
