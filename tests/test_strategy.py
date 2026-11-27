"""The exposure harness charges a change and leaves a constant book alone.

A constant exposure of 1 is buy and hold apart from the cost of opening
it. A change in exposure is charged the costs table on the size of the
change, and a missing funding value leaves the carry missing.
"""

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from regime_tester.costs import round_trip  # noqa: E402
from regime_tester.strategy import buy_and_hold, exposure_returns, rule_200d  # noqa: E402


def _close():
    index = pd.date_range("2024-01-01", periods=6, freq="D", tz="UTC")
    return pd.Series([100.0, 110.0, 121.0, 100.0, 100.0, 110.0], index=index)


class ConstantExposure(unittest.TestCase):
    def test_a_constant_exposure_of_1_matches_buy_and_hold_apart_from_the_opening_cost(self):
        close = _close()
        book = buy_and_hold(close)
        held = close.shift(-1) / close - 1
        self.assertAlmostEqual(book["cost"].iloc[0], round_trip(None))
        self.assertTrue((book["cost"].iloc[1:-1] == 0).all())
        pd.testing.assert_series_equal(
            book["net"].iloc[1:-1], held.iloc[1:-1], check_names=False)

    def test_a_change_in_exposure_is_charged(self):
        close = _close()
        exposure = pd.Series([1.0, 1.0, 0.0, 0.0, 1.0, 1.0], index=close.index)
        book = exposure_returns(close, exposure)
        self.assertAlmostEqual(book["cost"].iloc[2], round_trip(None))
        self.assertAlmostEqual(book["cost"].iloc[4], round_trip(None))
        self.assertEqual(book["cost"].iloc[1], 0.0)

    def test_a_missing_funding_value_leaves_the_carry_missing(self):
        close = _close()
        funding = pd.Series([0.01, None, 0.01, 0.01, 0.01, 0.01],
                             index=close.index, dtype="float")
        book = exposure_returns(close, pd.Series(1.0, index=close.index), funding)
        self.assertTrue(pd.isna(book["carry"].iloc[1]))
        self.assertTrue(pd.isna(book["net"].iloc[1]))
        self.assertAlmostEqual(book["carry"].iloc[0], 0.0001)


class Rule200(unittest.TestCase):
    def test_the_rule_is_flat_before_the_window_and_long_above_it(self):
        index = pd.date_range("2024-01-01", periods=210, freq="D", tz="UTC")
        close = pd.Series(range(100, 310), index=index, dtype="float")
        book = rule_200d(close)
        self.assertTrue((book["gross"].iloc[:199] == 0).all())
        self.assertGreater(book["gross"].iloc[200], 0)


if __name__ == "__main__":
    unittest.main()
