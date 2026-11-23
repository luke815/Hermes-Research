"""The G31 SMA change does not read a later bar.

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

from scripts.score_g31 import lookahead, sma_change


def _series(n=80):
    index = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    close = pd.Series(np.linspace(100, 180, n), index=index)
    return close


def centred_change(close):
    """The SMA change smoothed with a centred window. This reads the future."""
    return sma_change(close).rolling(5, center=True, min_periods=1).mean()


class SmaLookahead(unittest.TestCase):
    def test_a_later_price_does_not_move_the_signal(self):
        self.assertTrue(lookahead(_series()))

    def test_a_centred_window_fails_the_check(self):
        self.assertFalse(lookahead(_series(), builder=centred_change))


if __name__ == "__main__":
    unittest.main()
