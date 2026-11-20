"""The pooled Q1 rank uses only bars before the one it ranks."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, "/opt/data/.local/lib/python3.14/site-packages")

import numpy as np
import pandas as pd

from scripts.score_q1 import forward_drawdown, pooled_mean, trailing_percentile


class PooledRank(unittest.TestCase):
    def test_a_later_value_does_not_move_the_rank(self):
        index = pd.date_range("2024-01-01", periods=400, freq="D", tz="UTC")
        values = pd.Series(np.linspace(2, 1, 400), index=index)
        rank = trailing_percentile(values)
        later = values.copy()
        later.iloc[300:] = 100
        after = trailing_percentile(later)
        self.assertTrue(np.allclose(rank.iloc[:300], after.iloc[:300], equal_nan=True))
        self.assertFalse(np.allclose(rank.iloc[301:], after.iloc[301:], equal_nan=True))

    def test_a_short_history_stays_empty(self):
        index = pd.date_range("2024-01-01", periods=300, freq="D", tz="UTC")
        values = pd.Series(np.arange(300, dtype=float), index=index)
        rank = trailing_percentile(values)
        self.assertTrue(rank.iloc[:252].isna().all())
        self.assertTrue(rank.iloc[252:].notna().all())

    def test_a_panel_ranks_each_name_on_its_own_history(self):
        index = pd.date_range("2024-01-01", periods=400, freq="D", tz="UTC")
        frame = pd.DataFrame({
            "a": np.linspace(1, 2, 400),
            "b": np.linspace(5, 1, 400),
        }, index=index)
        rank = trailing_percentile(frame)
        alone = trailing_percentile(frame["a"])
        self.assertTrue(np.allclose(rank["a"], alone, equal_nan=True))
        self.assertGreater(rank["a"].iloc[-1], rank["b"].iloc[-1])

    def test_the_pooled_mean_drops_a_name_whose_signal_is_empty(self):
        index = pd.date_range("2024-01-01", periods=3, freq="D", tz="UTC")
        frame = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [9.0, 9.0, 9.0]}, index=index)
        defined = pd.DataFrame({"a": [True, True, True], "b": [False, False, False]},
                               index=index)
        pooled = pooled_mean(frame, defined)
        self.assertTrue(np.allclose(pooled.to_numpy(), [1.0, 2.0, 3.0]))

    def test_the_drawdown_ignores_a_bar_after_the_window(self):
        index = pd.date_range("2024-01-01", periods=6, freq="D", tz="UTC")
        price = pd.Series([10, 9, 8, 7, 1, 1], index=index, dtype=float)
        drawdown = forward_drawdown(price, 2)
        self.assertAlmostEqual(drawdown.iloc[0], 8 / 10 - 1)
        self.assertTrue(np.isnan(drawdown.iloc[-2]))


if __name__ == "__main__":
    unittest.main()
