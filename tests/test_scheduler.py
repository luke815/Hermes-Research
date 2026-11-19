"""A job that fails is not recorded as having run.

The scheduler writes a results file after every attempt, and already_ran
treats any file for today's slot as done. A script that exits non-zero then
blocks the slot for the rest of the day, so a job that failed at its minute
is never retried and the slot looks empty. A failed attempt must leave the
slot open.
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import scheduler  # noqa: E402


class FailedJob(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.results = scheduler.RESULTS
        scheduler.RESULTS = self.tmp.name

    def tearDown(self):
        scheduler.RESULTS = self.results
        self.tmp.cleanup()

    def test_a_failed_attempt_does_not_close_the_slot(self):
        now = datetime(2026, 11, 18, 5, 35, tzinfo=timezone.utc)
        job = {"name": "laevitas_refresh", "at": "05:35", "script": "scripts/laevitas_refresh.py"}
        scheduler.record(job, now, {"exit": 1, "ok": False, "tail": "boom"})
        self.assertFalse(scheduler.already_ran(job, now))

    def test_a_clean_run_closes_the_slot(self):
        now = datetime(2026, 11, 18, 5, 35, tzinfo=timezone.utc)
        job = {"name": "laevitas_refresh", "at": "05:35", "script": "scripts/laevitas_refresh.py"}
        scheduler.record(job, now, {"exit": 0, "ok": True, "tail": ""})
        self.assertTrue(scheduler.already_ran(job, now))
        saved = json.load(open(os.path.join(self.tmp.name, "2026-11-18_laevitas_refresh.json")))
        self.assertEqual(saved["result"]["exit"], 0)

    def test_an_hourly_run_does_not_close_the_next_hour(self):
        job = {"name": "intraday_backfill", "at": ":15", "script": "scripts/backfill_intraday.py"}
        first = datetime(2026, 11, 19, 1, 15, tzinfo=timezone.utc)
        scheduler.record(job, first, {"exit": 0, "ok": True, "tail": ""})
        nxt = datetime(2026, 11, 19, 2, 15, tzinfo=timezone.utc)
        self.assertTrue(scheduler.already_ran(job, first))
        self.assertFalse(scheduler.already_ran(job, nxt))
        self.assertTrue(os.path.exists(
            os.path.join(self.tmp.name, "2026-11-19T01_intraday_backfill.json")))


if __name__ == "__main__":
    unittest.main()
