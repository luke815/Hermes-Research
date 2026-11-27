"""C9 ranks on the lagged return and charges the carry in return units.

The reopened run divided funding by 10,000, which understated the carry by
about 100, and a rank that saw the forward return would pick the winners
after the move. Both must fail here.
"""

import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.score_c9_momentum import book, spread_on


def _frames():
    dates = pd.date_range("2024-01-01", periods=40, freq="D", tz="UTC")
    # AAA rises steadily, so its lagged 14-day return is positive.
    # ZZZ falls, so its lagged return is negative.
    aaa = pd.Series(np.linspace(100, 140, 40), index=dates, name="close")
    zzz = pd.Series(np.linspace(100, 60, 40), index=dates, name="close")
    frames = {}
    for coin, close, funding in (("AAA", aaa, 0.01), ("ZZZ", zzz, 0.01)):
        frame = pd.DataFrame({"close": close, "funding_rate": funding}, index=dates)
        frames[coin] = frame
    # Twenty flat names so a decile can form. Their funding is missing, so a
    # date that needs ten known-carry names is dropped rather than zeroed.
    for i in range(20):
        frames[f"N{i:02d}"] = pd.DataFrame(
            {"close": np.linspace(10, 10.4, 40), "funding_rate": np.nan}, index=dates)
    return frames


class CarryScale(unittest.TestCase):
    def test_carry_is_funding_divided_by_100(self):
        built = book(_frames())
        # One settlement of 0.01 percent is 0.0001 in return units, times the
        # 7-day window. The old divisor of 10,000 would give 1e-6 per day.
        carry = built["carry_7"]["AAA"].dropna()
        self.assertGreater(len(carry), 0)
        self.assertAlmostEqual(float(carry.iloc[0]), 7 * 0.01 / 100.0)

    def test_a_missing_carry_drops_the_date(self):
        built = book(_frames())
        scored = spread_on(built["mom_14"], built["gross_7"], built["carry_7"], 7)
        if scored.empty:
            return
        self.assertTrue(bool(scored["dropped_missing_carry"].all()))
        self.assertTrue(scored["spread"].isna().all())


class LaggedRank(unittest.TestCase):
    def test_a_later_price_does_not_move_the_signal(self):
        frames = _frames()
        first = book(frames)["mom_14"]["AAA"].copy()
        frames["AAA"].iloc[-1, frames["AAA"].columns.get_loc("close")] = 1.0
        second = book(frames)["mom_14"]["AAA"]
        # The last bar has no lagged 14-day window that includes itself, so
        # every earlier signal is unchanged when the last close is rewritten.
        shared = first.dropna().index.intersection(second.dropna().index)
        self.assertGreater(len(shared), 0)
        pd.testing.assert_series_equal(first.loc[shared], second.loc[shared])


if __name__ == "__main__":
    unittest.main()
