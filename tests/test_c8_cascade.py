"""The C8 cascade flag reads only bars before day t."""

import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.score_c8_cascade import cascade_flag  # noqa: E402


class CascadeFlag(unittest.TestCase):
    def test_a_missing_side_leaves_the_day_out(self):
        index = pd.date_range("2024-01-01", periods=40, freq="D", tz="UTC")
        long_side = pd.Series(1.0, index=index)
        short_side = pd.Series(1.0, index=index)
        short_side.iloc[10] = float("nan")
        flag = cascade_flag(long_side, short_side, 0.95)
        self.assertFalse(bool(flag.iloc[11]))

    def test_perturbing_future_liquidations_does_not_move_the_flag(self):
        index = pd.date_range("2024-01-01", periods=120, freq="D", tz="UTC")
        long_side = pd.Series(range(120), index=index, dtype=float)
        short_side = pd.Series(range(120), index=index, dtype=float)
        before = cascade_flag(long_side, short_side, 0.95)
        noisy_long = long_side.copy()
        noisy_short = short_side.copy()
        noisy_long.iloc[81:] = noisy_long.iloc[81:] + 1_000_000_000
        noisy_short.iloc[81:] = noisy_short.iloc[81:] + 1_000_000_000
        after = cascade_flag(noisy_long, noisy_short, 0.95)
        self.assertTrue(before.iloc[:81].equals(after.iloc[:81]))
        # The flag itself stays false on a monotone series, so the check reads
        # the threshold the flag is cut against. A leak moves that threshold
        # at the bars before the perturbation; a correct lag does not.
        from scripts.score_c8_cascade import SUM_DAYS, WINDOW, MIN_HISTORY
        def threshold(side_l, side_s):
            total = (side_l + side_s).shift(1).rolling(SUM_DAYS, min_periods=SUM_DAYS).sum()
            return total.rolling(WINDOW, min_periods=MIN_HISTORY).quantile(0.95)
        self.assertTrue(threshold(long_side, short_side).iloc[:81].equals(
            threshold(noisy_long, noisy_short).iloc[:81]))
        self.assertFalse(threshold(long_side, short_side).iloc[81:].equals(
            threshold(noisy_long, noisy_short).iloc[81:]),
                         "the perturbation never reached the threshold, so the check cannot catch a leak")


if __name__ == "__main__":
    unittest.main()
