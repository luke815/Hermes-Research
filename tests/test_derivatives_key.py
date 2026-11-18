"""The derivatives key is built from the store and refuses a stale one.

A planted series comes out with the right change and percentile, a day the
store does not hold stays absent, and a store whose newest day is more than
two behind today raises rather than writing a key dated as current.
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from regime_tester import derivatives
from scripts import build_derivatives_key as builder


def _rows(values, start, field="dvol"):
    idx = pd.date_range(start, periods=len(values), freq="D", tz="UTC")
    return [{"date": int(stamp.timestamp() * 1000), field: value} for stamp, value in zip(idx, values)]


class KeyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = derivatives.RAW
        self.store = Path(self.tmp.name)
        derivatives.RAW = self.store
        self.out = self.store / "derivatives.json"
        builder.OUT = str(self.out)

    def tearDown(self):
        derivatives.RAW = self.saved
        self.tmp.cleanup()

    def test_planted_series_reads_back(self):
        today = datetime.now(timezone.utc).date()
        start = (today - timedelta(days=59)).isoformat()
        values = list(range(1, 61))
        (self.store / "dvol_btc_a.json").write_text(json.dumps(_rows(values, start)))
        (self.store / "dvol_eth_a.json").write_text(json.dumps(_rows(values, start)))
        payload = builder.build()
        row = next(r for r in payload["assets"]["BTC"] if r["name"] == "dvol_level")
        self.assertEqual(row["value"], 60.0)
        self.assertEqual(row["chg_1d"], 1.0)
        self.assertEqual(row["chg_7d"], 7.0)
        self.assertEqual(len(row["spark"]), 30)
        self.assertEqual(row["spark"][-1], 60.0)
        self.assertEqual(row["as_of"], today.isoformat())
        self.assertIn("ETH", payload["assets"])

    def test_missing_day_is_absent(self):
        today = datetime.now(timezone.utc).date()
        start = (today - timedelta(days=9)).isoformat()
        (self.store / "dvol_btc_a.json").write_text(json.dumps(_rows(list(range(10)), start)))
        (self.store / "dvol_eth_a.json").write_text(json.dumps(_rows(list(range(10)), start)))
        payload = builder.build()
        names = {r["name"] for r in payload["assets"]["BTC"]}
        self.assertNotIn("atm_iv_7", names)
        self.assertNotIn("basis_venue", names)

    def test_stale_store_raises(self):
        start = (datetime.now(timezone.utc).date() - timedelta(days=40)).isoformat()
        (self.store / "dvol_btc_a.json").write_text(json.dumps(_rows(list(range(10)), start)))
        (self.store / "dvol_eth_a.json").write_text(json.dumps(_rows(list(range(10)), start)))
        with self.assertRaises(SystemExit):
            builder.build()
        self.assertFalse(self.out.exists())

    def test_a_stale_series_keeps_its_own_date(self):
        today = datetime.now(timezone.utc).date()
        fresh = (today - timedelta(days=59)).isoformat()
        stale = (today - timedelta(days=70)).isoformat()
        (self.store / "dvol_btc_a.json").write_text(json.dumps(_rows(list(range(1, 61)), fresh)))
        (self.store / "dvol_eth_a.json").write_text(json.dumps(_rows(list(range(1, 61)), fresh)))
        (self.store / "rr_btc_a.json").write_text(json.dumps(_rows(list(range(1, 41)), stale, field="30")))
        payload = builder.build()
        rr = next(r for r in payload["assets"]["BTC"] if r["name"] == "risk_reversal_30")
        dvol = next(r for r in payload["assets"]["BTC"] if r["name"] == "dvol_level")
        self.assertEqual(rr["as_of"], (today - timedelta(days=31)).isoformat())
        self.assertNotEqual(rr["as_of"], dvol["as_of"])
        self.assertEqual(payload["as_of"], today.isoformat())

    def test_raw_is_restored_after_the_class(self):
        """A later test must see the real store, not this class's temp copy."""
        self.assertTrue(self.saved.exists())
        self.assertNotEqual(derivatives.RAW, self.saved)


if __name__ == "__main__":
    unittest.main()
