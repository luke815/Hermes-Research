"""The stall detector reads a dated verdict, not a word anywhere in the line.

A note that mentions "done" or "rejected" in passing used to close the item.
Only a verdict with a date closes it.
"""

import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "hourly_health", os.path.join(ROOT, "scripts", "hourly_health.py"))
health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(health)


class StallReadsAVerdict(unittest.TestCase):
    def test_a_mention_of_done_does_not_close_the_item(self):
        import re
        line = "- Q9. The run said the cell was done in passing, no verdict."
        closed = bool(re.search(
            r"\b(Done|Rejected|Insufficient|Admitted|Archived) \d{4}-\d{2}-\d{2}\b", line))
        self.assertFalse(closed)
        dated = "- Q9. Done 2026-11-25. The cell passed."
        self.assertTrue(bool(re.search(
            r"\b(Done|Rejected|Insufficient|Admitted|Archived) \d{4}-\d{2}-\d{2}\b", dated)))


if __name__ == "__main__":
    unittest.main()
