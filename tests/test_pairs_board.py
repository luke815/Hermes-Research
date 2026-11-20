"""The pairs screen keeps a cointegrated pair and drops one that is not.

The Engle-Granger p-value is the part the page cannot check. A pair built from
one random walk and a lag of itself reverts and must come back below 0.05, and
two independent walks must not. The screen then keeps the reverting pair and
drops the other.
"""

import os
import sys
import unittest

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import build_pairs_board as board


def _walk(rng, n):
    return np.cumsum(rng.normal(size=n))


class Cointegration(unittest.TestCase):
    def test_a_cointegrated_pair_passes_and_two_walks_do_not(self):
        rng = np.random.default_rng(7)
        shared = _walk(rng, 120)
        residual = np.zeros(120)
        for i in range(1, 120):
            residual[i] = 0.2 * residual[i - 1] + rng.normal()
        left = shared + residual
        right = shared + rng.normal(size=120) * 0.01
        other = _walk(rng, 120)
        self.assertLess(board.engle_granger(left, right), 0.05)
        self.assertGreater(board.engle_granger(left, other), 0.05)

    def test_the_screen_keeps_only_the_reverting_pair(self):
        rows = [
            {"oi_long": 30_000_000, "oi_short": 30_000_000, "coint_p": 0.01,
             "half_life": 12, "z": -2.4, "long": "AAA", "short": "BBB"},
            {"oi_long": 30_000_000, "oi_short": 30_000_000, "coint_p": 0.40,
             "half_life": 12, "z": -3.0, "long": "CCC", "short": "DDD"},
            {"oi_long": 1_000, "oi_short": 30_000_000, "coint_p": 0.01,
             "half_life": 12, "z": -2.4, "long": "EEE", "short": "FFF"},
        ]
        kept = board.reversion_rows(rows)
        self.assertEqual([row["long"] for row in kept], ["AAA"])

    def test_the_same_coin_on_two_venues_is_not_a_pair(self):
        self.assertTrue(board._same_coin("XYZ:SNDK", "SNDK"))
        self.assertFalse(board._same_coin("NEAR", "ETH"))
        rows = [
            {"long": "AAA", "short": "BBB", "z": -2.4},
            {"long": "BBB", "short": "AAA", "z": 2.4},
            {"long": "CCC", "short": "DDD", "z": -2.1},
        ]
        self.assertEqual(len(board._dedupe(rows)), 2)


if __name__ == "__main__":
    unittest.main()
