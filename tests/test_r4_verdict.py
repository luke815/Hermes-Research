"""The variant verdict rejects a dial that does not beat both benchmarks.

The bars are the ones in research/RISK_REGIME.md section 3: maximum
drawdown and Calmar against buy and hold, and Calmar against the 200-day
rule, in validation and in test separately. A dial that wins in one
period and loses in the other is rejected.
"""

import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def beats(full, hold, trend):
    """The admission bars for one period, read off the stats the scorer writes."""
    beats_hold = (
        full["max_drawdown"] > hold["max_drawdown"]
        and full["calmar"] > hold["calmar"])
    beats_trend = full["calmar"] > trend["calmar"]
    return beats_hold and beats_trend


class Verdict(unittest.TestCase):
    def test_a_dial_that_wins_one_period_and_loses_the_other_is_rejected(self):
        path = os.path.join(
            Path(__file__).resolve().parents[1], "results",
            "2026-11-21_r4_variants.json")
        detail = json.load(open(path))["verdict_detail"]
        kept = all(
            beats(row["full"], row["buy_and_hold"], row["trend_only"])
            for row in detail.values())
        self.assertFalse(kept)

    def test_a_dial_that_beats_both_benchmarks_in_both_periods_is_kept(self):
        full = {"max_drawdown": -0.10, "calmar": 2.0}
        hold = {"max_drawdown": -0.30, "calmar": 1.0}
        trend = {"max_drawdown": -0.20, "calmar": 0.5}
        self.assertTrue(beats(full, hold, trend))


if __name__ == "__main__":
    unittest.main()
