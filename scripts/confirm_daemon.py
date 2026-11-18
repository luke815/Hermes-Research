"""Confirmation daemon. One eligible cell per cycle, no model involved.

Cross-sectional and event cells come first. A single-name cell is only tried
once every cross-sectional survivor on the leaderboard has been attempted.
A cell already in the confirmation record is skipped, and one whose expected
validation count is under 30 is never queued.

Usage: python3 scripts/confirm_daemon.py
"""

import json
import os
import sys

# procmgr restarts from a clean environment, which does not have the user
# site on its path. The libraries live there, so the script adds them itself.
_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD = os.path.join(ROOT, "results", "sweeps", "leaderboard.json")
RECORD = os.path.join(ROOT, "results", "sweeps", "confirmations.json")


def attempted():
    """Cells with a live verdict. A void row is not an attempt."""
    if not os.path.exists(RECORD):
        return set()
    return {row["cell_id"] for row in json.load(open(RECORD))
            if not str(row.get("verdict", "")).startswith("void")}


def eligible():
    board = json.load(open(BOARD)).get("leaderboard", [])
    done = attempted()
    fresh = [row for row in board if row["cell_id"] not in done
             and row.get("status") != "insufficient"
             and not row["cell_id"].split("|")[4].startswith(("rel_", "ratio_btc"))]
    cross = [row for row in fresh if row.get("universe") == "pit_cross_section"
             or "pit_cross_section" in row["cell_id"]]
    events = [row for row in fresh if row["cell_id"].split("|")[4].startswith(("top_", "bottom_"))]
    single = [row for row in fresh if row not in cross and row not in events]
    return cross + events + single


def _record_void(cell_id, reason):
    """Write a void row for a cell the current panel cannot score."""
    from datetime import datetime, timezone
    rows = json.load(open(RECORD)) if os.path.exists(RECORD) else []
    rows.append({
        "cell_id": cell_id,
        "verdict": "void",
        "void_reason": reason,
        "voided_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    tmp = RECORD + ".tmp"
    json.dump(rows, open(tmp, "w"), indent=2)
    os.replace(tmp, RECORD)


def cycle(ctx):
    queue = eligible()
    if not queue:
        return {"cell": None, "remaining": 0}
    cell = queue[0]
    from regime_tester.confirm import confirm_cell, family_attempts, family_of
    family = family_of(cell["cell_id"])
    try:
        record = confirm_cell(cell["cell_id"], family_n=family_attempts().get(family, 0),
                              train_sign=1 if cell.get("train_score", 0) > 0 else -1)
    except (ValueError, RuntimeError) as error:
        # Recorded as void so the queue moves on. A void row is not an attempt,
        # and the old reason is kept so the cell can be rebuilt later.
        _record_void(cell["cell_id"], str(error))
        return {"cell": cell["cell_id"], "verdict": "void",
                "error": str(error), "remaining": len(queue) - 1}
    return {"cell": cell["cell_id"], "verdict": record["verdict"],
            "family": family, "remaining": len(queue) - 1}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from daemon_base import run_loop
    run_loop("confirm", interval_sec=300, cycle=cycle, align=False)
