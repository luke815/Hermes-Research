"""The sweep reads high and low when the panel file carries them.

The loader used to name its columns and leave high and low off the list, so a
file that had both still scored as if the range did not exist. These tests pin
the rule: a column the file has is read, and a column it lacks is absent.
"""

import os
import sys
import tempfile
import textwrap
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))
import sweep_xs


class LoadPanelRange(unittest.TestCase):
    def test_high_and_low_are_read_when_the_file_has_them(self):
        with tempfile.TemporaryDirectory() as directory:
            _write(directory, "binance_AAAUSDT.csv", with_range=True)
            saved = sweep_xs.PANEL
            sweep_xs.PANEL = directory
            try:
                frames = sweep_xs.load_panel(["binance_AAAUSDT"])
            finally:
                sweep_xs.PANEL = saved
        frame = frames["binance_AAAUSDT"]
        self.assertIn("high", frame.columns)
        self.assertIn("low", frame.columns)
        self.assertEqual(frame["high"].iloc[0], 11.0)
        self.assertEqual(frame["low"].iloc[0], 9.0)

    def test_a_file_without_high_and_low_loads_without_them(self):
        with tempfile.TemporaryDirectory() as directory:
            _write(directory, "binance_BBBUSDT.csv", with_range=False)
            saved = sweep_xs.PANEL
            sweep_xs.PANEL = directory
            try:
                frames = sweep_xs.load_panel(["binance_BBBUSDT"])
            finally:
                sweep_xs.PANEL = saved
        frame = frames["binance_BBBUSDT"]
        self.assertNotIn("high", frame.columns)
        self.assertNotIn("low", frame.columns)
        self.assertIn("close", frame.columns)


class RangeAdmission(unittest.TestCase):
    def test_a_range_measure_is_scored_when_a_name_has_high_and_low(self):
        panel = {"binance_AAAUSDT": _frame(with_range=True, filled=True)}
        admitted = sweep_xs.scorable_measures(sweep_xs.panel_inputs(panel))
        self.assertIn("atr_14", admitted)
        self.assertIn("stoch_k", admitted)

    def test_a_range_measure_is_skipped_when_high_and_low_are_empty(self):
        panel = {"binance_AAAUSDT": _frame(with_range=True, filled=False)}
        admitted = sweep_xs.scorable_measures(sweep_xs.panel_inputs(panel))
        self.assertNotIn("atr_14", admitted)
        self.assertIn("rsi_14", admitted)

    def test_a_range_measure_is_skipped_when_the_file_has_no_range(self):
        panel = {"binance_AAAUSDT": _frame(with_range=False, filled=False)}
        admitted = sweep_xs.scorable_measures(sweep_xs.panel_inputs(panel))
        self.assertNotIn("atr_14", admitted)
        self.assertNotIn("high", sweep_xs.panel_inputs(panel))


def _frame(with_range, filled):
    import pandas as pd
    row = {"date": ["2024-01-01"], "close": [10.0], "volume_usd": [1000.0],
           "funding_rate": [0.01], "oi_usd": [3e7], "basis": [0.002],
           "long_short_ratio": [1.1]}
    if with_range:
        row["high"] = [11.0 if filled else float("nan")]
        row["low"] = [9.0 if filled else float("nan")]
    return pd.DataFrame(row).set_index("date")


def _write(directory, name, with_range):
    header = "date,close,volume_usd,funding_rate,oi_usd,basis,long_short_ratio"
    row = "2024-01-01,10,1000,0.01,30000000,0.002,1.1"
    if with_range:
        header += ",high,low"
        row += ",11,9"
    open(os.path.join(directory, name), "w").write(header + "\n" + row + "\n")


if __name__ == "__main__":
    unittest.main()
