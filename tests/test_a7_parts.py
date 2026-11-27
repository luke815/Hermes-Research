"""The A7 crowding rule, checked where it can fail.

A day is a pooled flag only when at least three of the five names are flagged,
and a missing name is not counted as flagged. The lift is the flagged rate
over the base rate, so a flag that picks the wrong days gives a lift below 1.
"""

import unittest

import numpy as np
import pandas as pd

from scripts.score_a7_rest import lift, POOLED_MIN, ALT_NAMES


class CrowdingRule(unittest.TestCase):
    def test_pooled_flag_needs_three_names(self):
        index = pd.date_range("2024-01-01", periods=4, tz="UTC")
        flags = {
            "ADA": [1, 1, 0, np.nan],
            "SOL": [1, 0, 0, 1],
            "LINK": [1, 0, 0, np.nan],
            "XRP": [0, 1, 0, np.nan],
            "AVAX": [0, 0, 0, np.nan],
        }
        stacked = pd.DataFrame(flags, index=index)
        count = stacked.sum(axis=1)
        pooled = (count >= POOLED_MIN).where(stacked.notna().any(axis=1))
        # two names is not a pool, and a missing name is not a flag
        self.assertEqual(list(pooled.astype(bool)),
                         [True, False, False, False])
        self.assertEqual(int(count.iloc[1]), 2)
        self.assertEqual(len(ALT_NAMES), 5)

    def test_lift_below_one_when_the_flag_misses(self):
        index = pd.date_range("2024-01-01", periods=4, tz="UTC")
        flag = pd.Series([True, False, False, False], index=index)
        label = pd.Series([False, True, True, False], index=index)
        reading = lift(flag, label)
        self.assertLess(reading["lift"], 1)
        self.assertEqual(reading["flagged"], 1)


if __name__ == "__main__":
    unittest.main()
