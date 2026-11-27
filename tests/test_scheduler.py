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

    def test_the_health_slot_writes_the_stall_line(self):
        # The health slot is the only thing that fires every hour. The stall
        # line has to be written there, or the health log never shows the check.
        now = datetime(2026, 11, 19, 6, 5, tzinfo=timezone.utc)
        called = []
        import sys as _sys
        stub = type("H", (), {"stall_check": staticmethod(
            lambda: called.append("ran") or "- A1. blocked")})()
        _sys.modules["hourly_health"] = stub
        self.addCleanup(lambda: _sys.modules.pop("hourly_health", None))
        scheduler.record = lambda job, n, result: called.append(result.get("stall"))
        scheduler.already_ran = lambda job, n: False
        scheduler.due = lambda job, n: job["name"] == "health"
        scheduler.JOBS = [{"name": "health", "at": ":05", "script": None}]
        try:
            scheduler.cycle(None)
        finally:
            import importlib
            importlib.reload(scheduler)
        self.assertIn("ran", called)
        self.assertTrue(any(c and "A1" in c for c in called))

    def test_counter_refresh_keeps_the_sweep_suffix(self):
        # The sweep writes its name count and rate onto the shared line. The
        # scheduler refreshes the counter part every cycle, and replacing the
        # whole line drops both, so the rate the clause reads never survives.
        with tempfile.TemporaryDirectory() as tmp:
            scheduler.STATUS = os.path.join(tmp, "sweep_status")
            scheduler.COUNTER = os.path.join(tmp, "counter.json")
            json.dump({"scored": 7, "testable": 9, "since": "2026-10-31",
                       "file": "results/sweeps/counter.json"},
                      open(scheduler.COUNTER, "w"))
            open(scheduler.STATUS, "w").write(
                "cells scored 7 of 9 testable since 2026-10-31, "
                "from results/sweeps/counter.json, names 234, cells per hour 0\n")
            written = scheduler.sweep_status()["line"]
            self.assertIn("names 234", written)
            self.assertIn("cells per hour 0", written)
            self.assertTrue(written.index("names 234") < written.index("cells per hour"))


if __name__ == "__main__":
    unittest.main()
