"""The rs_stale log measures an observed span, not a guessed one.

A5 needs the flag false for a full day. A gap between readings is time nobody
looked, and counting it would close the item on a flag that may have flipped.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.rs_stale_log import append, false_span_hours, read  # noqa: E402


def _row(hour, stale):
    return {"ts": f"2026-11-19T{hour:02d}:00:00Z", "rs_stale": stale, "rs_age_sec": 1000}


class RsStaleLogTests(unittest.TestCase):
    def test_a_gap_does_not_count_as_time_observed(self):
        rows = [_row(0, False), _row(1, False),
                {"ts": "2026-11-19T20:00:00Z", "rs_stale": False, "rs_age_sec": 1000},
                {"ts": "2026-11-19T21:00:00Z", "rs_stale": False, "rs_age_sec": 1000}]
        self.assertEqual(false_span_hours(rows), 1.0)

    def test_a_true_reading_ends_the_span(self):
        rows = [_row(0, False), _row(1, True), _row(2, False), _row(3, False)]
        self.assertEqual(false_span_hours(rows), 1.0)

    def test_a_repeated_timestamp_is_not_a_second_reading(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "log.jsonl")
            self.assertTrue(append(path, "2026-11-19T00:00:00Z", False, 1000))
            self.assertFalse(append(path, "2026-11-19T00:00:00Z", False, 1000))
            self.assertEqual(len(read(path)), 1)
            self.assertEqual(json.loads(open(path).read().strip())["rs_stale"], False)

    def test_nul_padding_does_not_crash_the_reader(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "log.jsonl")
            append(path, "2026-11-19T00:00:00Z", False, 1000)
            with open(path, "ab") as handle:
                handle.write(b"\x00" * 70)
            self.assertEqual(len(read(path)), 1)
            self.assertTrue(append(path, "2026-11-19T01:00:00Z", False, 1000))

    def test_no_reading_is_not_a_span(self):
        self.assertIsNone(false_span_hours([]))
        self.assertIsNone(false_span_hours([_row(5, True)]))
