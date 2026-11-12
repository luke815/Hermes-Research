"""Sweep statistics for the page. Reads the scored files and the confirmation record.

Writes the sweep key of dashboard/data.json: how many cells are scored, the
leaderboard's top per family, and the last 30 confirmations. Nothing is
recomputed.

Usage: python3 scripts/sweep_stats.py
"""

import json
import os
from datetime import datetime, timezone

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWEEPS = os.path.join(ROOT, "results", "sweeps")
DATA = os.path.join(ROOT, "dashboard", "data.json")


def main():
    files = sorted(f for f in os.listdir(SWEEPS) if f.endswith(".csv"))
    scored = sum(len(pd.read_csv(os.path.join(SWEEPS, f))) for f in files)
    board = json.load(open(os.path.join(SWEEPS, "leaderboard.json")))
    conf = json.load(open(os.path.join(SWEEPS, "confirmations.json")))
    payload = {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cells_tested": scored,
        "cells_enumerated": board.get("cells_enumerated"),
        "eligible": board.get("eligible"),
        "fragile": board.get("fragile"),
        "duplicates": board.get("duplicates"),
        "by_family": board.get("by_family", []),
        "leaderboard": board.get("leaderboard", [])[:20],
        "confirmations": [
            {"date": row.get("attempted_at", "")[:10], "cell_id": row["cell_id"],
             "validation_t": (row.get("validation") or {}).get("t_newey_west"),
             "bar": row.get("deflated_bar"), "n": (row.get("validation") or {}).get("n_independent"),
             "verdict": row.get("verdict")}
            for row in conf[-30:]
        ],
    }
    data = json.load(open(DATA))
    data["sweep"] = payload
    tmp = DATA + ".tmp"
    json.dump(data, open(tmp, "w"))
    os.replace(tmp, DATA)
    print(f"sweep cells {scored} confirmations {len(payload['confirmations'])}")


if __name__ == "__main__":
    main()
