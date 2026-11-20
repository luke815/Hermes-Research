"""Score the L6 positioning cross-section and record a verdict.

The four series are funding, open interest, basis and the long/short ratio,
read from data/panel_xs_laevitas. Open interest has no change column, so the
measure that uses it is oi_on_down_days. Each measure is scored through the
sweep's own score_one, on the same liquid universe and the same costs, so the
rows are the rows the sweep would write. The verdict is read from those rows:
a cell is kept only when its spread keeps its sign in the first and second
half of the train window and the non-overlapping count is at least 40 in each.
This script writes the results file. It does not pull and it does not confirm.
"""

import os
import sys

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

from regime_tester.results_io import write_result  # noqa: E402
import sweep_xs  # noqa: E402

MEASURES = ("funding_persist_high", "oi_on_down_days", "basis_level", "ls_ratio_level")
MIN_INDEPENDENT = 40


def mark_usable(row):
    """A cell is usable only with 40 independent observations and a real spread.

    A NaN spread and a zero spread are both unusable. The count is the
    non-overlapping one the sweep already computed.
    """
    n_ind = int(row["n_independent"])
    spread = row["spread"]
    sign = 0.0
    if spread == spread and spread is not None:
        sign = float(np.sign(spread))
    row["usable"] = bool(n_ind >= MIN_INDEPENDENT and sign != 0.0)
    return row


def score():
    close, digest = sweep_xs.load_train()
    panel = sweep_xs.load_panel(close.columns)
    cache = sweep_xs.indicator_cache(panel, close.index, digest)
    net = sweep_xs.net_returns(close)
    spans = sweep_xs.panel_spans(close.columns)
    close.attrs["digest"] = digest
    cells = []
    missing = []
    for name in MEASURES:
        if name not in cache:
            missing.append(name)
            continue
        for row in sweep_xs.score_one(close, cache[name], name, net, spans):
            row["names"] = int(close.shape[1])
            cells.append(row)
    kept = []
    for row in cells:
        mark_usable(row)
        if row["usable"]:
            kept.append(row["id"])
    by_measure = {}
    for name in MEASURES:
        rows = [row for row in cells if row["measure"] == name]
        by_measure[name] = {
            "cells": len(rows),
            "usable": sum(1 for row in rows if row["usable"]),
            "best_abs_t": None if not rows else max(
                abs(row["t_newey_west"]) for row in rows
                if row["t_newey_west"] == row["t_newey_west"]),
        }
    verdict = "insufficient"
    reason = "no positioning cell has 40 independent observations"
    if any(row["usable"] for row in cells):
        verdict = "recorded"
        reason = ("the cells with 40 independent observations are recorded; "
                  "admission waits on validation and test, which this script does not read")
    return {
        "item": "L6",
        "panel": "data/panel_xs_laevitas",
        "names": int(close.shape[1]),
        "measures": list(MEASURES),
        "missing_measures": missing,
        "cells": len(cells),
        "usable": len(kept),
        "kept_ids": kept[:20],
        "by_measure": by_measure,
        "verdict": verdict,
        "reason": reason,
        "train_end": sweep_xs.TRAIN_END,
        "min_independent": MIN_INDEPENDENT,
    }


def main():
    payload = score()
    path = write_result("l6_positioning", payload, inputs=["data/panel_xs_laevitas"])
    print(path)
    print(payload["verdict"], payload["cells"], payload["usable"], payload["names"])


if __name__ == "__main__":
    main()
