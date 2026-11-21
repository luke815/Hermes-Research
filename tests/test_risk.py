"""The risk dial uses only the past, and a gap is unavailable, not calm."""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from regime_tester.risk import (  # noqa: E402
    dial_of, inputs_on, percentile, readings, run_states, unavailable, weekly_position,
)


def _close(days, drift):
    index = pd.date_range("2024-01-01", periods=days, freq="D", tz="UTC")
    return pd.Series(100 * np.exp(np.cumsum(np.full(days, drift))), index=index)


class Percentile(unittest.TestCase):
    def test_a_later_value_does_not_move_an_earlier_percentile(self):
        series = pd.Series(np.arange(60, dtype=float))
        before = percentile(series, window=40, minimum=10)
        series.iloc[-1] = 10_000
        after = percentile(series, window=40, minimum=10)
        pd.testing.assert_series_equal(before.iloc[:-1], after.iloc[:-1])

    def test_the_window_excludes_today(self):
        series = pd.Series([1.0] * 40 + [100.0])
        self.assertEqual(percentile(series, window=40, minimum=10).iloc[-1], 1.0)


class WeeklyBand(unittest.TestCase):
    def test_a_price_later_in_the_week_does_not_move_monday(self):
        close = _close(400, 0.001)
        before, _, _ = weekly_position(close)
        bumped = close.copy()
        bumped.iloc[-1] *= 3
        after, _, _ = weekly_position(bumped)
        pd.testing.assert_series_equal(before.iloc[:-1], after.iloc[:-1])


class Lookahead(unittest.TestCase):
    def test_a_later_price_does_not_move_an_earlier_reading(self):
        close = _close(500, 0.001)
        panel = pd.DataFrame({"btc_price": close, "eth_price": close * 0.05,
                               "alt_price": close * 0.3, "basis_btc": 1.0})
        before = readings(panel, pd.DataFrame(index=close.index))
        bumped = panel.copy()
        bumped.loc[bumped.index[-1], ["btc_price", "eth_price", "alt_price"]] *= 3
        after = readings(bumped, pd.DataFrame(index=close.index))
        pd.testing.assert_frame_equal(before.iloc[:-1], after.iloc[:-1])


class Inputs(unittest.TestCase):
    def test_a_missing_series_is_unavailable(self):
        got = inputs_on({"btc_vs_200d": 1.2})
        by_name = {row["name"]: row for row in got}
        self.assertEqual(by_name["btc_vs_200d"]["flag"], "above")
        self.assertFalse(by_name["breadth_above_50d"]["available"])
        self.assertEqual(by_name["stablecoin_supply_30d"]["flag"], "unavailable")
        self.assertEqual(unavailable("dxy_30d")["effect"], "none")


class StateMachine(unittest.TestCase):
    def _frame(self, days, drift):
        close = _close(days, drift)
        panel = pd.DataFrame({"btc_price": close, "eth_price": close * 0.05,
                               "alt_price": close, "basis_btc": 1.0})
        return readings(panel, pd.DataFrame(index=close.index))

    def test_a_rising_market_is_risk_on_and_a_falling_one_is_risk_off(self):
        up = run_states(self._frame(500, 0.002))
        down = run_states(self._frame(500, -0.002))
        self.assertEqual(up["state"].iloc[-1], "risk_on_trend")
        self.assertIn(down["state"].iloc[-1], ("risk_off_trend_down", "risk_off_distribution"))

    def test_hysteresis_holds_a_state_inside_five_days(self):
        frame = self._frame(500, 0.002)
        # the state changed three days ago, so a one-day flip cannot move it yet
        frame.iloc[-3:, frame.columns.get_loc("btc_vs_200d")] = -20.0
        frame.iloc[-3:, frame.columns.get_loc("weekly_position")] = "below"
        walked = run_states(frame)
        flipped = frame.copy()
        flipped.iloc[-1, flipped.columns.get_loc("btc_vs_200d")] = 20.0
        flipped.iloc[-1, flipped.columns.get_loc("weekly_position")] = "above"
        held = run_states(flipped)
        self.assertEqual(walked["state"].iloc[-1], "risk_off_trend_down")
        self.assertEqual(held["state"].iloc[-1], "risk_off_trend_down")

    def test_the_dial_stays_inside_the_state_band_scaled(self):
        dial = dial_of("neutral", 1.0)
        self.assertGreaterEqual(dial, 0.60 * 0.5)
        self.assertLessEqual(dial, 0.80 * 1.3)
        self.assertAlmostEqual(dial, 0.70, places=4)


if __name__ == "__main__":
    unittest.main()
