"""The G30 Mayer z-score does not read a later bar.

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

from scripts.score_g30 import lookahead, mayer_z


def _series(n=400):
    """A price that drifts, then drifts harder. A flat z-score would hide a leak."""
    index = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    step = np.where(np.arange(n) < n // 2, 0.2, 1.5)
    close = pd.Series(100 + np.cumsum(step), index=index)
    return close


def centred_z(close):
    """The Mayer z-score smoothed with a centred window. This reads the future."""
    scored = mayer_z(close)
    return scored.rolling(5, center=True, min_periods=1).mean()


class MayerLookahead(unittest.TestCase):
    def test_a_later_price_does_not_move_the_signal(self):
        self.assertTrue(lookahead(_series()))

    def test_a_centred_window_fails_the_check(self):
        self.assertFalse(lookahead(_series(), builder=centred_z))


if __name__ == "__main__":
    unittest.main()
