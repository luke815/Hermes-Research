"""A late-starting series is scored only where it is defined.

H1: a signal that starts in 2021 scored against a price panel that starts in
2019 must give the same excess as the same series scored on a panel that
starts in 2021. The bars before the signal exists are not part of the
comparison set, for the excess or for the unflagged mean.
"""

import os
import sys
import unittest

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "research", "outside", "harness"))
sys.path.insert(0, ROOT)

import harness2  # noqa: E402
from regime_tester.sweep import score_signal  # noqa: E402


def _panel():
    """A 2019-start price panel and a signal defined only from 2021."""
    dates = pd.date_range("2019-01-01", "2021-06-30", freq="D", tz="UTC")
    rng = np.random.default_rng(7)
    forward = pd.Series(rng.normal(0.002, 0.01, len(dates)), index=dates)
    defined = dates >= "2021-01-01"
    signal = pd.Series(np.where(defined, (np.arange(len(dates)) % 5 == 0), np.nan),
                       index=dates)
    return forward, signal, defined


class LateStart(unittest.TestCase):
    def test_a_2021_start_series_matches_a_2021_start_panel(self):
        forward, signal, defined = _panel()
        full = harness2.score_flag(
            signal.fillna(False).astype(bool), forward,
            pd.Series(0.0, index=forward.index), cost=0.0, h=1, freq="1d",
            valid=pd.Series(defined, index=forward.index))
        cut = forward.index >= "2021-01-01"
        short = harness2.score_flag(
            signal[cut].astype(bool), forward[cut],
            pd.Series(0.0, index=forward.index[cut]), cost=0.0, h=1, freq="1d",
            valid=pd.Series(True, index=forward.index[cut]))
        self.assertIsNotNone(full["train"]["excess"])
        self.assertAlmostEqual(full["train"]["excess"], short["train"]["excess"], places=12)
        self.assertEqual(full["train"]["n_bars"], short["train"]["n_bars"])

    def test_the_unflagged_mean_excludes_bars_before_the_signal(self):
        forward, signal, defined = _panel()
        scored = harness2.score_flag(
            signal.fillna(False).astype(bool), forward,
            pd.Series(0.0, index=forward.index), cost=0.0, h=1, freq="1d",
            valid=pd.Series(defined, index=forward.index))
        early = forward.index < "2021-01-01"
        self.assertGreater(int(early.sum()), 0)
        self.assertLess(scored["train"]["n_bars"], int((forward.index <= "2024-06-30").sum()))

    def test_the_house_scorer_drops_bars_before_the_signal(self):
        dates = pd.date_range("2019-01-01", periods=800, freq="D", tz="UTC")
        rng = np.random.default_rng(3)
        forward = rng.normal(0.0, 0.01, len(dates))
        signal = np.full(len(dates), -1.0)
        signal[400:] = (np.arange(400) % 4 == 0).astype(float)
        years = {year: (dates.year == year) for year in (2019, 2020, 2021)}
        full = score_signal(signal, forward, 1, years)
        late = score_signal(signal[400:], forward[400:], 1,
                            {2021: years[2021][400:]})
        self.assertIsNotNone(full)
        self.assertAlmostEqual(full["spread"], late["spread"], places=12)


if __name__ == "__main__":
    unittest.main()
