"""The P3 verdict admits only a positive spread that clears the bar.

A negative spread that is large is a loss, not an edge, so the sign of the
t-stat matters. These tests pin that rule.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))
import score_p3


def _summary(train, validation, test, n=40, t=2.0):
    return {
        "train": {"mean": train, "n": n, "t": t},
        "validation": {"mean": validation, "n": n, "t": t},
        "test": {"mean": test, "n": n, "t": t},
    }


class Verdict(unittest.TestCase):
    def test_a_negative_spread_in_every_period_is_not_admitted(self):
        got = score_p3._verdict(_summary(-0.01, -0.04, -0.003))
        self.assertNotEqual(got, "admitted")

    def test_a_spread_that_flips_sign_is_rejected(self):
        got = score_p3._verdict(_summary(0.01, -0.02, 0.01, t=3.0))
        self.assertEqual(got, "rejected")

    def test_a_positive_spread_below_the_t_bar_is_insufficient(self):
        got = score_p3._verdict(_summary(0.01, 0.02, 0.01, t=1.0))
        self.assertEqual(got, "insufficient")

    def test_a_positive_spread_clearing_the_bar_is_admitted(self):
        got = score_p3._verdict(_summary(0.01, 0.02, 0.01, t=2.5))
        self.assertEqual(got, "admitted")


if __name__ == "__main__":
    unittest.main()
