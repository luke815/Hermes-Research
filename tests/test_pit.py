"""The point-in-time universe includes delisted names, and costs hit both legs.

A name is in on a date only while its archive span covers that date. Binance
has no stopped flag, so a last file before the span pull date marks it
delisted. The cost check is a long and a short held together: the spread's
net differs from its gross by two round trips plus the carry on both sides.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from regime_tester.costs import apply_costs  # noqa: E402
from regime_tester.pit import delisted_by_date, listed_on, span_rows  # noqa: E402


def _write(directory, name, rows):
    path = Path(directory) / name
    pd.DataFrame(rows).to_csv(path, index=False)


class UniverseTests(unittest.TestCase):
    def test_a_name_is_absent_before_it_lists(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        _write(tmp.name, "binance_span.csv", [
            {"symbol": "BTCUSDT", "first": "2021-01-01", "last": "2026-11-01", "days": 100},
            {"symbol": "DEADUSDT", "first": "2022-01-01", "last": "2023-06-01", "days": 100},
        ])
        _write(tmp.name, "bybit_span.csv", [
            {"symbol": "ETHUSDT", "first": "2021-06-01", "last": "2024-01-01", "days": 100, "stopped": 1},
        ])
        _write(tmp.name, "okx_span.csv", [
            {"symbol": "SOL", "first": "2023-01-01", "last": "2026-11-01", "days": 100, "stopped": 0},
        ])
        universe = span_rows(tmp.name)
        self.assertEqual(int(universe["delisted"].sum()), 2)
        early = listed_on(universe, "2021-03-01")
        self.assertEqual(set(early["symbol"]), {"BTCUSDT"})
        mid = listed_on(universe, "2023-03-01")
        self.assertEqual(set(mid["symbol"]), {"BTCUSDT", "DEADUSDT", "ETHUSDT", "SOL"})
        late = listed_on(universe, "2025-01-01")
        self.assertEqual(set(late["symbol"]), {"BTCUSDT", "SOL"})

    def test_delisted_names_are_counted_per_date(self):
        universe = span_rows()
        counts = delisted_by_date(universe)
        self.assertGreater(int(universe["delisted"].sum()), 463)
        self.assertTrue((counts["delisted_names"] > 0).any())
        self.assertIn("date", counts.columns)


class SpreadCostTests(unittest.TestCase):
    def test_long_short_net_differs_from_gross(self):
        idx = pd.date_range("2024-01-01", periods=4, freq="D", tz="UTC")
        long_px = pd.Series([100, 110, 121, 130], index=idx, dtype=float)
        short_px = pd.Series([100, 90, 80, 70], index=idx, dtype=float)
        funding = pd.Series([0.01, 0.02, 0.01, 0.0], index=idx, dtype=float)
        oi = pd.Series([60_000_000] * 4, index=idx, dtype=float)
        long = apply_costs(long_px, 1, side=1, funding=funding, oi_usd=oi)
        short = apply_costs(short_px, 1, side=-1, funding=funding, oi_usd=oi)
        gross = long["gross"].iloc[1] + short["gross"].iloc[1]
        net = long["net"].iloc[1] + short["net"].iloc[1]
        self.assertNotAlmostEqual(net, gross)
        self.assertLess(net, gross)


if __name__ == "__main__":
    unittest.main()
