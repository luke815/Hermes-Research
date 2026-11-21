"""Record the Q1 verdicts from the cells the scorer already wrote.

The panel is not re-read. The saved cells carry the three targets per window
and period, and verdict_of is the rule the pre-registration states. A window
that flips sign between validation and test is rejected; one below the
episode bar is insufficient. The watch card is written from the same file.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from regime_tester.results_io import write_result  # noqa: E402
from score_q1 import verdict_of  # noqa: E402
from build_q1_key import card  # noqa: E402
from dashboard_io import write_key  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "results", "2026-11-20_q1_lsr_drawdown.json")
KEY = os.path.join(ROOT, "dashboard", "keys", "q1.json")


def apply(reading):
    """Replace each cell's verdict with the one the rule produces."""
    cells = []
    for cell in reading["cells"]:
        corrected = dict(cell)
        corrected["verdict"] = verdict_of(cell["periods"], cell["episodes"])
        cells.append(corrected)
    return cells


def main():
    reading = json.load(open(SOURCE))
    cells = apply(reading)
    payload = {
        "prereg_commit": reading["prereg_commit"],
        "pooled_names": reading["pooled_names"],
        "lookahead_passed": reading["lookahead_passed"],
        "source": os.path.basename(SOURCE),
        "cells": cells,
    }
    path = write_result("q1_lsr_drawdown", payload, inputs=[SOURCE])
    written = card(payload, path)
    write_key(KEY, written)
    print(json.dumps({
        "path": path,
        "verdicts": [cell["verdict"] for cell in cells],
        "key": KEY,
    }))


if __name__ == "__main__":
    main()
