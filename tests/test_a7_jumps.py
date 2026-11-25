"""Two consecutive jump days are both prints, not one.

A single bad day between two real closes is extreme against both neighbours.
Two bad days in a row each have one neighbour that is itself a print, so a
rule that only looks one day either side keeps both. The rule looks past a
neighbour that is itself extreme.
"""

import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.score_a7_reversal import drop_jumps  # noqa: E402


class JumpDays(unittest.TestCase):
    def test_two_consecutive_jump_days_are_both_dropped(self):
        close = pd.DataFrame({"PEPE": [0.005, 5.7, 5.7, 0.005, 0.005]})
        out, changed = drop_jumps(close)
        self.assertEqual(changed, 2)
        self.assertTrue(np.isnan(out["PEPE"].iloc[1]))
        self.assertTrue(np.isnan(out["PEPE"].iloc[2]))
        self.assertEqual(out["PEPE"].iloc[0], 0.005)


if __name__ == "__main__":
    unittest.main()
