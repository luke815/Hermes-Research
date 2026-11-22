"""The range backfill must page klines and not mark a short write done.

Binance returns at most 1500 daily bars per call, and the newest window is
what one call returns. A name whose panel starts before that window was
marked done with high and low on the last few days only, so the range
measures still had nothing to score.
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts"))
import backfill_high_low as hl  # noqa: E402


def _bars(n, start):
    day = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    rows = []
    for i in range(n):
        stamp = int((day + timedelta(days=i)).timestamp() * 1000)
        rows.append([stamp, "1", "2", "0.5", "1.5", "10"])
    return rows


class HighLowPages(unittest.TestCase):
    def test_pages_past_one_window(self):
        calls = []

        def getter(url, timeout=30):
            calls.append(url)
            if "endTime=" not in url:
                return __import__("json").dumps(_bars(1500, "2022-10-06"))
            return __import__("json").dumps(_bars(100, "2018-08-28"))

        got = hl.klines("LINKUSDT", getter)
        self.assertGreater(len(calls), 1)
        self.assertEqual(len(got), 1600)
        self.assertIn("2018-08-28", got)
        self.assertIn("2022-10-06", got)

    def test_a_short_column_stays_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "binance_LINKUSDT.csv")
            with open(path, "w") as handle:
                handle.write("date,close,high,low\n")
                handle.write("2020-01-01,1,,\n")
                handle.write("2026-11-21,1,2,0.5\n")
            self.assertFalse(hl.column_complete(path))
            with open(path, "w") as handle:
                handle.write("date,close,high,low\n")
                handle.write("2020-01-01,1,2,0.5\n")
                handle.write("2026-11-21,1,2,0.5\n")
            self.assertTrue(hl.column_complete(path))


if __name__ == "__main__":
    unittest.main()
