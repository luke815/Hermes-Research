"""The G28 on-balance volume does not read a later bar.

A centred window does. The scorer's own check must reject one, so a
passing run means the check can catch a leak.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, "/opt/data/.local/lib/python3.14/site-packages")

import numpy as np
import pandas as pd

from scripts.score_g28 import lookahead, on_balance


def _series(n=40):
    index = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    close = pd.Series(np.linspace(100, 140, n), index=index)
    volume = pd.Series(np.linspace(10, 20, n), index=index)
    return close, volume


def centred_balance(close, volume):
    """On-balance volume smoothed with a centred window. This reads the future."""
    return on_balance(close, volume).rolling(5, center=True, min_periods=1).mean()


class ObvLookahead(unittest.TestCase):
    def test_a_later_price_does_not_move_the_signal(self):
        close, volume = _series()
        self.assertTrue(lookahead(close, volume))

    def test_a_centred_window_fails_the_check(self):
        close, volume = _series()
        self.assertFalse(lookahead(close, volume, builder=centred_balance))


if __name__ == "__main__":
    unittest.main()
