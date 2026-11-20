"""The L6 positioning scorer marks a cell usable only past the count bar.

A cell with fewer than 40 independent observations is not usable, a zero or
missing spread is not usable, and a measure the panel cannot build is named
as missing rather than filled.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import score_l6_positioning as scorer


class PositioningVerdict(unittest.TestCase):
    def test_a_thin_cell_is_not_usable_and_a_full_one_is(self):
        thin = scorer.mark_usable(
            {"n_independent": 12, "spread": 0.01})
        full = scorer.mark_usable(
            {"n_independent": 40, "spread": -0.02})
        zero = scorer.mark_usable(
            {"n_independent": 80, "spread": 0.0})
        blank = scorer.mark_usable(
            {"n_independent": 80, "spread": float("nan")})
        self.assertFalse(thin["usable"])
        self.assertTrue(full["usable"])
        self.assertFalse(zero["usable"])
        self.assertFalse(blank["usable"])

    def test_a_missing_measure_is_named(self):
        cache = {"basis_level": object()}
        missing = [name for name in scorer.MEASURES if name not in cache]
        self.assertIn("funding_persist_high", missing)
        self.assertIn("oi_on_down_days", missing)
        self.assertNotIn("basis_level", missing)


if __name__ == "__main__":
    unittest.main()
