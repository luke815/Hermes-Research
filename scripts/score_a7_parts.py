"""Write the three A7 results files the done-when clause names.

A7(2), A7(3) and A7(4) are scored by scripts/score_a7_rest.py from the
pre-registration in research/outside/PREREG_A7.md. That script writes one
combined file. The backlog clause names three files, so this script scores
the same rules and writes each part under the name the clause asks for.

A7(2)'s filter on A7(1) is reported as not scored. A7(1) was rejected, and a
filter on a rejected score is not a second verdict. A7(4) is the two-name
reading the pre-registration specifies, not a cross-sectional decile.
"""

import os
import sys

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402
from scripts.score_a7_rest import (  # noqa: E402
    PREREG, prereg_commit, score_crowding, score_derivatives,
    score_funding, both_assets, lookahead_check)

import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = "data/panel.csv"
STORE = "data/laevitas/market"


def panel():
    frame = pd.read_csv(os.path.join(ROOT, PANEL), index_col=0)
    frame.index = pd.to_datetime(frame.index, utc=True)
    return frame


def main():
    commit = prereg_commit()
    frame = panel()
    derivatives = score_derivatives(frame)
    both_assets(derivatives)
    crowding = score_crowding()
    funding = score_funding(frame)
    inputs = [PANEL, STORE, PREREG]
    derivatives_path = write_result("a7_derivatives", {
        "prereg_commit": commit,
        "panel": STORE,
        "lookahead_passed": lookahead_check(frame),
        "cells": derivatives,
        "filter_on_a7_1": "not scored: A7(1) was rejected, so a filter on it "
                          "is not a verdict",
    }, inputs=inputs)
    crowding_path = write_result("a7_crowding", {
        "prereg_commit": commit,
        "panel": STORE,
        "date_clustered": True,
        "pooled_flag": "at least three of the five names flagged that day",
        "a7_3": crowding,
    }, inputs=inputs)
    funding_path = write_result("a7_funding", {
        "prereg_commit": commit,
        "panel": PANEL,
        "carry_charged": True,
        "scope": "two names, the market-level reading the pre-registration "
                 "specifies; it does not close a cross-sectional clause",
        "cells": funding,
    }, inputs=inputs)
    print(derivatives_path)
    print(crowding_path)
    print(funding_path)


if __name__ == "__main__":
    main()
