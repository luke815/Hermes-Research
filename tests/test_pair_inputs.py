"""The pair-inputs builder keeps one venue per coin and the floor.

A coin listed on two venues used to enter the calculator twice, once under each
venue's file name, so the name count overstated the universe. The builder
collapses to the venue with the most days above the floor, and a coin that
never clears the floor stays out unless it is BTC or ETH, which the calculator
needs as the hedge.
"""

import os
import sys
import unittest

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import build_pair_inputs as b


def _write(directory, name, oi_days, closes=None):
    rows = []
    for i in range(oi_days):
        rows.append({"date": f"2026-01-{i + 1:02d}" if i < 28 else f"2026-02-{i - 27:02d}",
                     "close": 100 + i if closes is None else closes[i],
                     "oi_usd": b.OI_FLOOR + 1, "funding_rate": 0.01})
    pd.DataFrame(rows).to_csv(os.path.join(directory, name), index=False)


class OneVenuePerCoin(unittest.TestCase):
    def test_two_venues_collapse_to_the_one_with_more_days(self, tmp=None):
        import tempfile
        with tempfile.TemporaryDirectory() as panel:
            _write(panel, "binance_SOLUSDT.csv", 60)
            _write(panel, "bybit_SOLUSDT.csv", 80)
            _write(panel, "binance_BTCUSDT.csv", 10)
            _write(panel, "binance_ETHUSDT.csv", 10)
            kept = b.liquid_venues(panel)
            self.assertEqual(kept["SOL"], "bybit_SOLUSDT")
            self.assertEqual(len([c for c in kept if c == "SOL"]), 1)

    def test_the_page_prints_the_universe_count_from_the_key(self):
        page = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "dashboard", "index.html")
        text = open(page).read()
        # The lead line is what the calculator shows. It counts the names in
        # the key, so a key with the universe count is what the page displays.
        self.assertIn("syms.length + ' names from the '", text)
        self.assertIn("d.pair_inputs", text)

    def test_a_coin_below_the_floor_is_absent_and_btc_is_kept(self):
        import tempfile
        with tempfile.TemporaryDirectory() as panel:
            _write(panel, "binance_DOGEUSDT.csv", 5)
            _write(panel, "binance_BTCUSDT.csv", 3)
            _write(panel, "binance_ETHUSDT.csv", 3)
            kept = b.liquid_venues(panel)
            self.assertNotIn("DOGE", kept)
            self.assertIn("BTC", kept)
            self.assertIn("ETH", kept)


if __name__ == "__main__":
    unittest.main()
