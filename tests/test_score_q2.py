"""The Q2 item verdict follows the cells, and a thin window is not a rejection."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.score_q2 import EPISODE_BAR, item_verdict, verdict_of


def _fresh(episodes, effect=None):
    row = {"episodes": episodes, "window": "2026"}
    if effect is not None:
        row["effect"] = effect
    return row


class ItemVerdict(unittest.TestCase):
    def test_a_window_below_the_bar_is_insufficient_not_rejected(self):
        # The 2026 window has 5 episodes on BTC against a bar of 20. The old
        # scorer left the item with no verdict word, so a thin window read as
        # not scored. A count below the bar is insufficient even when the
        # effect has a sign.
        self.assertLess(5, EPISODE_BAR)
        thin = verdict_of([_fresh(0), _fresh(5, -0.032522)])
        self.assertEqual(thin, "insufficient")
        signed = verdict_of([_fresh(EPISODE_BAR, 0.01), _fresh(EPISODE_BAR, -0.01)])
        self.assertEqual(signed, "rejected")

    def test_one_insufficient_cell_makes_the_item_insufficient(self):
        cells = [{"verdict": "kept"}, {"verdict": "insufficient"},
                 {"verdict": "rejected"}]
        self.assertEqual(item_verdict(cells), "insufficient")
        self.assertEqual(item_verdict([{"verdict": "rejected"}]), "rejected")
        self.assertEqual(item_verdict([{"verdict": "kept"}, {"verdict": "kept"}]), "kept")
        with self.assertRaises(ValueError):
            item_verdict([])


if __name__ == "__main__":
    unittest.main()
