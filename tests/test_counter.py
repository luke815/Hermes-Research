"""The sweep counter has one writer, and the digest reads the same file."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester import counter  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import digest_counter  # noqa: E402


class CounterTests(unittest.TestCase):
    def test_digest_and_status_cite_the_same_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            counter.COUNTER = os.path.join(tmp, "counter.json")
            counter.STATUS = os.path.join(tmp, "sweep_status")
            counter.write_counter(4, 10)
            saved = json.load(open(counter.COUNTER))
            self.assertEqual(saved["scored"], 4)
            self.assertEqual(saved["testable"], 10)
            text = digest_counter.line()
            self.assertIn("4", text)
            self.assertIn("10", text)
            self.assertIn(saved["file"], text)


if __name__ == "__main__":
    unittest.main()
