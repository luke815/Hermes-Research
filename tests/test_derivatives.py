"""Tests for the market-level derivatives and options measures.

The lookahead check is the same one the price indicators pass: perturbing every
value after day t must not move the measure at t. A planted run must come out as
that run, and a series the store does not hold must be absent rather than filled.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from regime_tester import derivatives  # noqa: E402
from regime_tester.derivatives import (  # noqa: E402
    DERIVATIVES_META, _percentile, _persistence, daily, market_measures, tenor,
)


def _write(directory, name, rows):
    (directory / name).write_text(json.dumps(rows))


def _rows(values, start="2021-01-01", **extra):
    idx = pd.date_range(start, periods=len(values), freq="D", tz="UTC")
    rows = []
    for stamp, value in zip(idx, values):
        row = {"date": int(stamp.timestamp() * 1000)}
        row.update({k: (v if not callable(v) else v(value)) for k, v in extra.items()})
        if not extra:
            row["value"] = value
        rows.append(row)
    return rows


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        derivatives.RAW = Path(self.tmp.name)

    def test_overlapping_windows_keep_the_last_row(self):
        first = [{"date": 1609459200000, "dvol": 40.0}]
        second = [{"date": 1609459200000, "dvol": 55.0}]
        _write(derivatives.RAW, "dvol_btc_a.json", first)
        _write(derivatives.RAW, "dvol_btc_b.json", second)
        series = daily("dvol_btc*.json", lambda r: r.get("dvol"))
        self.assertEqual(series.iloc[0], 55.0)

    def test_a_row_with_no_value_is_a_gap(self):
        rows = [{"date": 1609459200000, "dvol": 40.0}, {"date": 1609545600000}]
        _write(derivatives.RAW, "dvol_btc_a.json", rows)
        series = daily("dvol_btc*.json", lambda r: r.get("dvol"))
        self.assertEqual(len(series), 1)

    def test_sub_daily_rows_collapse_to_the_day(self):
        rows = [
            {"date": 1609459200000, "dvol": 40.0},
            {"date": 1609470000000, "dvol": 42.0},
        ]
        _write(derivatives.RAW, "dvol_btc_a.json", rows)
        series = daily("dvol_btc*.json", lambda r: r.get("dvol"))
        self.assertEqual(len(series), 1)
        self.assertEqual(series.iloc[0], 42.0)

    def test_missing_series_is_absent(self):
        out = market_measures()
        self.assertEqual(list(out.columns), [])

    def test_planted_term_inversion_is_flagged(self):
        rows = _rows([50.0] * 10, **{"7": 60.0, "90": 40.0})
        _write(derivatives.RAW, "atmiv_btc_1.json", rows)
        out = market_measures()
        self.assertTrue((out["atm_term_slope_btc"] == -20.0).all())
        self.assertTrue((out["atm_inversion_btc"] == 1.0).all())

    def test_venue_mean_ignores_a_venue_that_did_not_report(self):
        rows = [{"date": 1609459200000, "BINANCE": 10.0, "OKX": 20.0}]
        _write(derivatives.RAW, "basis_btc_a.json", rows)
        out = market_measures()
        self.assertEqual(out["basis_venue_btc"].iloc[0], 15.0)

    def test_tenor_mean_does_not_read_a_venue_column(self):
        from regime_tester.derivatives import tenor_mean
        row = {"date": 1, "BINANCE": 100.0, "30": 6.0, "90": 8.0}
        self.assertEqual(tenor_mean(row), 7.0)


class LookaheadTests(unittest.TestCase):
    def test_percentile_does_not_see_the_future(self):
        rng = np.random.default_rng(3)
        values = pd.Series(rng.normal(0, 1, 400))
        base = _percentile(values)
        perturbed = values.copy()
        perturbed.iloc[201:] = 100
        again = _percentile(perturbed)
        self.assertTrue(np.allclose(base.iloc[:201], again.iloc[:201], equal_nan=True))

    def test_persistence_counts_only_the_past(self):
        values = pd.Series(np.linspace(0, 1, 120))
        high, low = _persistence(values, window=60, min_periods=30)
        perturbed = values.copy()
        perturbed.iloc[90:] = -5
        again_high, again_low = _persistence(perturbed, window=60, min_periods=30)
        self.assertTrue(np.array_equal(high.iloc[:90], again_high.iloc[:90]))
        self.assertTrue(np.array_equal(low.iloc[:90], again_low.iloc[:90]))

    def test_a_planted_hot_run_counts_up(self):
        values = pd.Series(list(np.linspace(0, 1, 100)) + [5, 5, 5, 5])
        high, _ = _persistence(values, window=60, min_periods=30)
        self.assertGreater(high.iloc[-1], 1)


class RealStoreTests(unittest.TestCase):
    def test_the_store_serves_both_assets(self):
        out = market_measures()
        self.assertIn("dvol_level_btc", out.columns)
        self.assertIn("dvol_level_eth", out.columns)
        self.assertGreater(out["dvol_level_btc"].notna().sum(), 1000)
        for name in DERIVATIVES_META:
            self.assertIn(f"{name}_btc", out.columns, name)

    def test_short_series_are_absent(self):
        out = market_measures()
        self.assertFalse(any("basis_slope" in c or "butterfly" in c for c in out.columns))


if __name__ == "__main__":
    unittest.main()
