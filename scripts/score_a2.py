"""A2: score one cross-sectional cell through the sweep path and record it.

The confirmer used to raise on every cross-sectional cell because it was
handed no panel. This scores the first cross-sectional cell on the
leaderboard through the sweep's own net, two times 15 basis points, on a
sample of the Laevitas panel, and writes the verdict. A cell that cannot be
scored is voided, not retried.

Usage: python3 scripts/score_a2.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regime_tester.confirm import (
    XS_COST_BPS, _load_cross_batch, confirm_cell, family_attempts, family_of,
)
from regime_tester.results_io import write_result

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD = os.path.join(ROOT, "results", "sweeps", "leaderboard.json")
PANEL = os.path.join(ROOT, "data", "panel_xs_laevitas")
SAMPLE = 60


def first_cross_section():
    board = json.load(open(BOARD)).get("leaderboard", [])
    for row in board:
        if "pit_cross_section" in row["cell_id"] and not row["cell_id"].split("|")[4].startswith("rel_"):
            return row
    raise SystemExit("the leaderboard has no cross-sectional cell")


def main():
    row = first_cross_section()
    names = sorted(n[:-4] for n in os.listdir(PANEL) if n.endswith(".csv"))[:SAMPLE]
    panel = _load_cross_batch(names)
    family = family_of(row["cell_id"])
    record = confirm_cell(row["cell_id"], family_n=family_attempts().get(family, 0),
                          train_sign=1 if row.get("train_score", 0) > 0 else -1, panel=panel)
    payload = {
        "cell_id": row["cell_id"],
        "verdict": record["verdict"],
        "void_reason": record.get("void_reason"),
        "cost_bps_per_side": XS_COST_BPS,
        "cost_note": "spread net of two times 15 bps, the sweep's thin tier, one long and one short",
        "names_scored": len(panel),
        "validation_n": None if record.get("validation") is None else record["validation"]["n_independent"],
        "test_n": None if record.get("test") is None else record["test"]["n_independent"],
    }
    path = write_result("a2_confirm", payload, inputs=["data/panel_xs_laevitas",
                                                       "results/sweeps/leaderboard.json"])
    print(json.dumps({"path": path, **payload}))


if __name__ == "__main__":
    main()
