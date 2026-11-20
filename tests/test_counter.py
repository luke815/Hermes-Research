"""The sweep counter has one writer, and the digest reads the same file.

The count covers every scoring path since the last admission. A file dated
before that date is not counted, and a file the counter did not read does not
move the number.
"""

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
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        counter.COUNTER = os.path.join(self.tmp.name, "counter.json")
        counter.SWEEPS = self.tmp.name
        counter.SPACE = os.path.join(self.tmp.name, "space.json")

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, name, ids):
        with open(os.path.join(self.tmp.name, name), "w") as handle:
            handle.write("id\n" + "\n".join(ids) + "\n")

    def test_digest_and_status_cite_the_same_number(self):
        self._write("2026-11-05.csv", ["a|raw", "b|raw"])
        payload = counter.write_counter()
        text = digest_counter.line()
        self.assertEqual(text, counter.status_text(payload))
        self.assertIn(str(payload["scored"]), text)
        self.assertIn(str(payload["testable"]), text)
        self.assertIn(payload["file"], text)
        self.assertEqual(payload["scored"], 2)

    def test_both_scoring_paths_are_counted_once(self):
        # The single-name sweep and the vectorized sweep write different files.
        # A cell saved by both is one cell, not two.
        self._write("2026-11-05.csv", ["a|raw", "b|raw"])
        self._write("2026-11-17_xs_vec.csv", ["b|raw", "c|raw"])
        payload = counter.write_counter()
        self.assertEqual(payload["scored"], 3)
        self.assertEqual(len(payload["files"]), 2)

    def test_a_file_before_the_last_admission_is_not_counted(self):
        self._write("2026-10-30.csv", ["old|raw"])
        self._write("2026-11-05.csv", ["new|raw"])
        payload = counter.write_counter()
        self.assertEqual(payload["scored"], 1)
        self.assertEqual(payload["since"], "2026-10-31")
