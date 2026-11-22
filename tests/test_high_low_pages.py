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


# The stall test replaces the module function and must restore this one.
hl_backfill = hl.backfill


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

    def test_a_failing_name_does_not_stall_the_next(self):
        with tempfile.TemporaryDirectory() as tmp:
            panel = os.path.join(tmp, "panel")
            os.makedirs(panel)
            for name in ("binance_AERGOUSDT.csv", "binance_LINKUSDT.csv"):
                with open(os.path.join(panel, name), "w") as handle:
                    handle.write("date,close\n2020-01-01,1\n")
            old_panel, old_progress, old_deferred = hl.PANEL, hl.PROGRESS, hl.DEFERRED
            hl.PANEL = panel
            hl.PROGRESS = os.path.join(tmp, "progress.json")
            hl.DEFERRED = os.path.join(tmp, "deferred.json")
            try:
                def fail_first(name, getter=None):
                    if name == "binance_AERGOUSDT.csv":
                        return 0
                    path = os.path.join(panel, name)
                    with open(path, "w") as handle:
                        handle.write("date,close,high,low\n2020-01-01,1,2,0.5\n")
                    return 1

                hl.backfill = fail_first
                first = hl.cycle(None)
                self.assertEqual(first["name"], "binance_AERGOUSDT.csv")
                self.assertEqual(first["deferred"], 1)
                second = hl.cycle(None)
                self.assertEqual(second["name"], "binance_LINKUSDT.csv")
                self.assertNotIn("deferred", second)
            finally:
                hl.PANEL, hl.PROGRESS, hl.DEFERRED = old_panel, old_progress, old_deferred
                hl.backfill = hl_backfill


if __name__ == "__main__":
    unittest.main()
