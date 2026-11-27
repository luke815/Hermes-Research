"""The weekly note names the week's changes, the whipsaws and the paper track.

Read from the results file the weekly script wrote, so a note that dropped
one of them fails here.
"""

import json
import os
import unittest
from pathlib import Path


class WeeklyNote(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        with open(os.path.join(root, "results", "2026-11-21_r6_weekly.json")) as handle:
            self.reading = json.load(handle)
        self.note = open(os.path.join(root, "research", "weekly_2026-11-21.md")).read()

    def test_the_note_names_the_changes_the_whipsaws_and_the_paper_track(self):
        self.assertIn("State changes this week", self.note)
        self.assertIn("Whipsaws", self.note)
        self.assertIn("Paper track", self.note)
        self.assertIn("Unavailable inputs", self.note)
        self.assertEqual(self.reading["whipsaws_this_week"], 0)


if __name__ == "__main__":
    unittest.main()
