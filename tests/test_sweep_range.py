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


def _write(directory, name, with_range):
    header = "date,close,volume_usd,funding_rate,oi_usd,basis,long_short_ratio"
    row = "2024-01-01,10,1000,0.01,30000000,0.002,1.1"
    if with_range:
        header += ",high,low"
        row += ",11,9"
    open(os.path.join(directory, name), "w").write(header + "\n" + row + "\n")


if __name__ == "__main__":
    unittest.main()
