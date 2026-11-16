"""The Laevitas puller finishes perpetuals before it opens the futures store."""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import laevitas_pull as pull  # noqa: E402


def _day_ms(text):
    return int(datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


class PullOrder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.perp = os.path.join(self.root, "perpetuals")
        self.fut = os.path.join(self.root, "futures")
        os.makedirs(self.perp)
        pull.STORE = self.perp
        pull.FUTURES_STORE = self.fut
        pull.INSTRUMENTS = os.path.join(self.root, "instruments.json")
        json.dump([
            {"market": "BINANCE", "type": "perpetual", "instrument": "BTCUSDT", "currency": "BTC"},
            {"market": "BINANCE", "type": "future", "instrument": "BTCUSDT_261225", "currency": "BTC"},
        ], open(pull.INSTRUMENTS, "w"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_capped_file_stays_pending_and_futures_wait(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        json.dump({
            "meta": {"total_pages": 3, "total": 2000},
            "pages_fetched": 2,
            "items": [{"date": _day_ms("2024-01-01")}],
        }, open(os.path.join(self.perp, "BINANCE_BTCUSDT.json"), "w"))
        left = pull.pending()
        self.assertEqual([r["instrument"] for r in left], ["BTCUSDT"])
        self.assertFalse(os.path.isdir(self.fut))

    def test_current_perpetual_opens_the_futures_store(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        json.dump({
            "meta": {"total_pages": 1, "total": 1},
            "pages_fetched": 1,
            "items": [{"date": _day_ms(today)}],
        }, open(os.path.join(self.perp, "BINANCE_BTCUSDT.json"), "w"))
        left = pull.pending()
        self.assertEqual([r["instrument"] for r in left], ["BTCUSDT_261225"])
        self.assertEqual(left[0]["type"], "future")


if __name__ == "__main__":
    unittest.main()
