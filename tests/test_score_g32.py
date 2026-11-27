"""The G32 force-index z-score does not read a later bar.

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

from scripts.score_g32 import force_z, lookahead


def _series(n=400):
    """A price and a volume that both drift. A flat z-score would hide a leak."""
    index = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    step = np.where(np.arange(n) < n // 2, 0.2, 1.5)
    close = pd.Series(100 + np.cumsum(step), index=index)
    volume = pd.Series(np.linspace(1_000, 5_000, n), index=index)
    return close, volume


def centred_z(close, volume):
    """The force z-score smoothed with a centred window. This reads the future."""
    scored = force_z(close, volume)
    return scored.rolling(5, center=True, min_periods=1).mean()


class ForceLookahead(unittest.TestCase):
    def test_a_later_price_does_not_move_the_signal(self):
        close, volume = _series()
        self.assertTrue(lookahead(close, volume))

    def test_a_centred_window_fails_the_check(self):
        close, volume = _series()
        self.assertFalse(lookahead(close, volume, builder=centred_z))


if __name__ == "__main__":
    unittest.main()
