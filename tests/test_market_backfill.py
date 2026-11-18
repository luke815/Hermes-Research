"""The market backfill resumes from saved pages and counts missing days."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import market_backfill as backfill  # noqa: E402


class Resume(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        backfill.STORE = os.path.join(self.tmp.name, "market")
        backfill.ROOT = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_saved_page_is_not_fetched_again(self):
        name, currency, route, first = backfill.SERIES[0]
        start, end = backfill.windows(first, "2020-10-01")[0]
        backfill.save_page(name, currency, route, start, end, 1, {
            "meta": {"total": 2, "items": 1, "total_pages": 2},
            "items": [{"date": 1600992000000, "pc": 1.0}],
        })
        pending = backfill.pending_page("2020-10-01")
        self.assertEqual(pending[:5], (name, currency, route, start, end))
        self.assertEqual(pending[5], 2)

    def test_a_finished_window_is_skipped(self):
        name, currency, route, first = backfill.SERIES[0]
        start, end = backfill.windows(first, "2020-10-01")[0]
        backfill.save_page(name, currency, route, start, end, 1, {
            "meta": {"total": 1, "items": 1, "total_pages": 1},
            "items": [{"date": 1600992000000, "pc": 1.0}],
        })
        pending = backfill.pending_page("2020-09-26")
        self.assertNotEqual((pending[0], pending[1]), (name, currency))

    def test_missing_days_are_counted_from_the_files(self):
        name, currency, route, _first = backfill.SERIES[0]
        backfill.save_page(name, currency, route, "2020-09-25", "2020-09-27", 1, {
            "meta": {"total": 2, "items": 2, "total_pages": 1},
            "items": [{"date": 1600992000000}, {"date": 1601164800000}],
        })
        rows = {row["series"]: row for row in backfill.coverage()}
        self.assertEqual(rows["oi_pc_ratio_BTC"]["rows"], 2)
        self.assertEqual(rows["oi_pc_ratio_BTC"]["missing_days"], 1)
        self.assertIsNone(rows["oi_pc_ratio_ETH"]["first"])

    def test_cycle_saves_before_asking_for_the_next(self):
        calls = []

        def getter(url, headers, timeout, allowance):
            calls.append(url)
            return {"meta": {"total": 1, "items": 1, "total_pages": 1},
                    "items": [{"date": 1600992000000, "pc": 0.4}]}

        result = backfill.cycle(None, getter)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["page"], 1)
        self.assertTrue(os.path.exists(os.path.join(backfill.STORE, "oi_pc_ratio_BTC_2020-09-25.json")))
        again = backfill.pending_page("2020-09-26")
        self.assertNotEqual((again[0], again[1]), ("oi_pc_ratio", "BTC"))


if __name__ == "__main__":
    unittest.main()
