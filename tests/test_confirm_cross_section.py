"""A cross-sectional confirmation scores the cell it is given.

Two cells with different measures must not share a validation statistic, which
is what happened when every cell was scored as 14-day momentum. A rel_ target
is refused, because it is the same test as its ret_ twin. The deflated bar
counts validation attempts in the family, and that count only rises. A void
row is not an attempt, so a void cell can be scored again.
"""

import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from a2_void import void_pre_fix  # noqa: E402
from regime_tester.confirm import (  # noqa: E402
    _score_cross_section, family_attempts, family_of, hac_t, parse_cell_id,
)


def _panel():
    rng = np.random.default_rng(7)
    dates = pd.date_range("2024-01-01", periods=420, freq="D", tz="UTC")
    panel = {}
    for i in range(24):
        close = 100 * np.exp(np.cumsum(rng.normal(0.0004, 0.02, len(dates))))
        panel[f"n{i}"] = pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "close": close})
    return panel


def _cell(measure, target="ret_1"):
    return parse_cell_id(
        f"{measure}|raw|above|80|{target}|pit_cross_section|none|daily")


class ConfirmCrossSection(unittest.TestCase):
    def test_two_cells_differ(self):
        panel = _panel()
        first = _score_cross_section(_cell("roc_12"), panel)
        second = _score_cross_section(_cell("mayer_multiple"), panel)
        self.assertNotEqual(first["validation"]["t_newey_west"],
                            second["validation"]["t_newey_west"])
        self.assertNotEqual(first["validation"]["spread_independent"],
                            second["validation"]["spread_independent"])

    def test_horizon_changes_the_statistic_and_the_label(self):
        panel = _panel()
        one = _score_cross_section(_cell("roc_12", "ret_1"), panel)
        three = _score_cross_section(_cell("roc_12", "ret_3"), panel)
        self.assertIn("t_newey_west", one["validation"])
        self.assertNotIn("t_newey_west", three["validation"])
        self.assertIn("hac_t", three["validation"])
        self.assertEqual(three["horizon"], 3)

    def test_rel_target_is_refused(self):
        with self.assertRaises(ValueError):
            parse_cell_id("roc_12|raw|above|80|rel_1|pit_cross_section|none|daily")

    def test_family_count_only_rises(self):
        rows = [
            {"cell_id": "roc_12|raw|above|80|ret_1|btc|none|daily", "validation": {"n": 1}},
            {"cell_id": "roc_12|raw|above|90|ret_1|btc|none|daily", "validation": {"n": 1}},
            {"cell_id": "sma_20|raw|above|80|ret_1|btc|none|daily", "validation": None},
        ]
        counts = family_attempts(rows)
        self.assertEqual(family_of(rows[0]["cell_id"]), "momentum")
        self.assertEqual(counts["momentum"], 2)
        self.assertNotIn("trend", counts)
        counts["momentum"] += 1
        self.assertEqual(family_attempts(rows)["momentum"], 2)

    def test_overlapping_t_is_not_labelled_newey_west(self):
        values = np.arange(12, dtype=float)
        self.assertEqual(set(hac_t(values, 1)), {"t_newey_west"})
        self.assertEqual(set(hac_t(values, 10)), {"hac_t"})
        self.assertNotEqual(hac_t(values, 10)["hac_t"], hac_t(values, 1)["t_newey_west"])

    def test_pre_fix_rows_become_void_and_keep_the_old_text(self):
        rows = [
            {"cell_id": "roc_12|raw|above|80|ret_1|pit_cross_section|none|daily",
             "verdict": "void: scored on 14-day momentum, not the cell"},
            {"cell_id": "mayer_multiple|raw|above|80|ret_1|pit_cross_section|none|daily",
             "verdict": "rejected"},
            {"cell_id": "sma_20|raw|above|80|ret_1|btc|none|daily", "verdict": "rejected"},
        ]
        changed = void_pre_fix(rows)
        self.assertEqual(changed, 2)
        self.assertEqual(rows[0]["verdict"], "void")
        self.assertEqual(rows[1]["verdict"], "void")
        self.assertEqual(rows[0]["void_before"],
                         "void: scored on 14-day momentum, not the cell")
        self.assertEqual(rows[2]["verdict"], "rejected")
        self.assertEqual(void_pre_fix(rows), 0)


if __name__ == "__main__":
    unittest.main()
