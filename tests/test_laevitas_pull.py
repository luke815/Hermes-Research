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

    def test_yesterdays_bar_is_current_so_futures_stay_open(self):
        yesterday = (datetime.now(timezone.utc).date().toordinal() - 1)
        text = datetime.fromordinal(yesterday).strftime("%Y-%m-%d")
        json.dump({
            "meta": {"total_pages": 2, "total": 1001},
            "pages_fetched": 1,
            "items": [{"date": _day_ms(text)}],
        }, open(os.path.join(self.perp, "BINANCE_BTCUSDT.json"), "w"))
        left = pull.pending()
        self.assertEqual(left[0]["type"], "future")
        self.assertEqual(left[0]["instrument"], "BTCUSDT_261225")

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

    def _current(self, folder, name):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        os.makedirs(folder, exist_ok=True)
        json.dump({
            "meta": {"total_pages": 1, "total": 1},
            "pages_fetched": 1,
            "items": [{"date": _day_ms(today)}],
        }, open(os.path.join(folder, name), "w"))

    def test_futures_finish_before_options_and_liquidations(self):
        self._current(self.perp, "BINANCE_BTCUSDT.json")
        left = pull.pending()
        self.assertEqual(left[0]["type"], "future")
        self._current(self.fut, "BINANCE_BTCUSDT_261225.json")
        pull.OPTION_CONTRACTS = os.path.join(self.root, "option_contracts.json")
        pull.OPTION_MATURITIES = os.path.join(self.root, "option_maturities.json")
        pull.OPTIONS_STORE = os.path.join(self.root, "options")
        pull.LIQUIDATIONS_STORE = os.path.join(self.root, "liquidations")
        pull.CATALOG = os.path.join(self.root, "catalog.json")
        json.dump({"params": {"maturities": {"data": {
            "deribit": {"BTC": ["25DEC26"]},
        }}}}, open(pull.CATALOG, "w"))
        left = pull.pending()
        self.assertEqual(left[0].get("list"), True)
        self.assertFalse(os.path.isdir(pull.LIQUIDATIONS_STORE))
        json.dump([{
            "market": "DERIBIT", "type": "option", "currency": "BTC",
            "instrument": "BTC-25DEC26-20000-C", "expiry": "25DEC26",
        }], open(pull.OPTION_CONTRACTS, "w"))
        json.dump([["DERIBIT", "BTC", "25DEC26"]], open(pull.OPTION_MATURITIES, "w"))
        left = pull.pending()
        self.assertEqual(left[0]["instrument"], "BTC-25DEC26-20000-C")
        self.assertEqual(left[0]["type"], "option")
        self._current(pull.OPTIONS_STORE, "DERIBIT_BTC-25DEC26-20000-C.json")
        left = pull.pending()
        self.assertEqual(left[0]["type"], "liquidation")
        self.assertIn("BTC", [r["instrument"] for r in left])

    def test_one_saved_strike_does_not_finish_the_maturity(self):
        self._current(self.perp, "BINANCE_BTCUSDT.json")
        self._current(self.fut, "BINANCE_BTCUSDT_261225.json")
        pull.OPTION_CONTRACTS = os.path.join(self.root, "option_contracts.json")
        pull.OPTION_MATURITIES = os.path.join(self.root, "option_maturities.json")
        pull.OPTIONS_STORE = os.path.join(self.root, "options")
        pull.LIQUIDATIONS_STORE = os.path.join(self.root, "liquidations")
        pull.CATALOG = os.path.join(self.root, "catalog.json")
        json.dump({"params": {"maturities": {"data": {
            "deribit": {"TRX": ["17NOV26", "18NOV26"]},
        }}}}, open(pull.CATALOG, "w"))
        json.dump([{
            "market": "DERIBIT", "type": "option", "currency": "TRX",
            "instrument": "TRX_USDC-18NOV26-0d31-P", "expiry": "18NOV26",
        }], open(pull.OPTION_CONTRACTS, "w"))
        left = pull.pending()
        self.assertEqual(left[0].get("list"), True)
        self.assertFalse(os.path.isdir(pull.LIQUIDATIONS_STORE))
        # An empty call is still walked, so the next cycle moves on.
        json.dump([["DERIBIT", "TRX", "17NOV26"]], open(pull.OPTION_MATURITIES, "w"))
        left = pull.pending()
        self.assertEqual(left[0].get("list"), True)
        json.dump([
            ["DERIBIT", "TRX", "17NOV26"],
            ["DERIBIT", "TRX", "18NOV26"],
        ], open(pull.OPTION_MATURITIES, "w"))
        left = pull.pending()
        self.assertEqual(left[0]["type"], "option")
        self.assertEqual(left[0]["instrument"], "TRX_USDC-18NOV26-0d31-P")


if __name__ == "__main__":
    unittest.main()
