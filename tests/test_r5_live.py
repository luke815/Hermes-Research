"""The live record names ten analogs and starts the paper track on the key's day.

Both are read from the results file the scorer wrote, so a run that wrote
fewer analogs or started the track on a different day fails here.
"""

import json
import os
import unittest
from pathlib import Path


class LiveRecord(unittest.TestCase):
    def setUp(self):
        path = os.path.join(
            Path(__file__).resolve().parents[1], "results",
            "2026-11-21_r5_live.json")
        with open(path) as handle:
            self.reading = json.load(handle)

    def test_ten_analogs_each_carry_both_forward_returns(self):
        rows = self.reading["analogs"]
        self.assertEqual(len(rows), 10)
        for row in rows:
            self.assertIn("fwd_10", row)
            self.assertIn("fwd_30", row)

    def test_the_paper_track_starts_the_day_the_key_first_existed(self):
        self.assertEqual(self.reading["paper"]["since"], self.reading["as_of"])


if __name__ == "__main__":
    unittest.main()
