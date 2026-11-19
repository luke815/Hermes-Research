"""The delisted puller walks the span files and skips a name already saved."""

import json
import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import delisted_pull as pull  # noqa: E402


class Walk(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.spans = pull.VENUES
        self.store = pull.STORE
        self.root = pull.ROOT
        pull.ROOT = self.tmp.name
        pull.STORE = os.path.join(self.tmp.name, "delisted")
        spans = os.path.join(self.tmp.name, "data")
        os.makedirs(spans)
        open(os.path.join(spans, "binance_span.csv"), "w").write(
            "symbol,first,last,days\nLUNAUSDT,2021-01-01,2022-05-12,400\nBTCUSDT,2020-01-01,2026-11-18,2000\n")
        open(os.path.join(spans, "bybit_span.csv"), "w").write(
            "symbol,first,last,days,stopped\nFTTUSDT,2021-01-01,2022-11-14,600,1\n")
        open(os.path.join(spans, "okx_span.csv"), "w").write(
            "symbol,first,last,days,stopped\nSRM,2021-01-01,2022-12-12,700,1\n")
        pull.VENUES = (
            ("data/binance_span.csv", "BINANCE", lambda symbol: symbol),
            ("data/bybit_span.csv", "BYBIT", lambda symbol: symbol),
            ("data/okx_span.csv", "OKX", lambda symbol: f"{symbol}-USDT-SWAP"),
        )

    def tearDown(self):
        pull.VENUES = self.spans
        pull.STORE = self.store
        pull.ROOT = self.root
        self.tmp.cleanup()

    def test_a_live_name_is_not_queued_and_a_saved_name_is_skipped(self):
        dead = pull.dead_names("2026-11-19")
        self.assertEqual([row["symbol"] for row in dead], ["LUNAUSDT", "FTTUSDT", "SRM"])
        self.assertEqual(dead[2]["instrument"], "SRM-USDT-SWAP")
        asked = []

        def getter(url, headers, timeout, allowance):
            asked.append(url)
            return {"meta": {"total_pages": 1}, "items": [{"date": 1652313600000}]}

        first = pull.cycle(None, getter)
        self.assertEqual(first["instrument"], "LUNAUSDT")
        self.assertEqual(len(asked), 1)
        again = pull.pending("2026-11-19")
        self.assertNotIn("LUNAUSDT", [row["symbol"] for row in again])

    def test_a_404_is_recorded_and_retried_after_7_days(self):
        def missing(url, headers, timeout, allowance):
            raise urllib.error.HTTPError(url, 404, "nope", hdrs=None, fp=None)

        result = pull.cycle(None, missing)
        self.assertEqual(result["code"], 404)
        self.assertEqual(pull.pending("2026-11-19")[0]["symbol"], "FTTUSDT")
        self.assertTrue(any(row["symbol"] == "LUNAUSDT" for row in pull.pending("2026-11-26")))


if __name__ == "__main__":
    unittest.main()
