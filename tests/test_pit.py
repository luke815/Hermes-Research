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

import numpy as np
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
        # Both legs pay a round trip, and the long pays the carry the short receives.
        both_legs = long["round_trip"].iloc[1] + short["round_trip"].iloc[1]
        both_carry = long["carry"].iloc[1] + short["carry"].iloc[1]
        self.assertAlmostEqual(gross - net, both_legs + both_carry)
        self.assertGreater(both_legs, long["round_trip"].iloc[1])
        # A long pays positive funding and a short receives it, so the two carries
        # are equal and opposite and the spread's carry is their sum, not one leg's.
        self.assertAlmostEqual(short["carry"].iloc[1], -long["carry"].iloc[1])
        self.assertNotAlmostEqual(long["carry"].iloc[1], 0.0)


class ListingMaskTests(unittest.TestCase):
    def test_a_dead_name_changes_the_rank_before_the_mask_and_not_after(self):
        from regime_tester.cross_section import score_cross_section
        from scripts.sweep_xs import _spreads
        dates = pd.date_range("2024-01-01", periods=25, freq="D")
        days = dates.strftime("%Y-%m-%d")
        panel = {}
        for i in range(22):
            # A rising close, so the forward return is not flat and the decile has a sign.
            close = pd.Series(np.linspace(100.0, 100.0 + (i + 1) * 5, len(days)), index=days)
            panel[f"live{i}"] = pd.DataFrame({"date": days, "close": close.to_numpy()})
        # Dead on every date of the window, and the only falling name, so it takes the bottom decile.
        panel["dead"] = pd.DataFrame({"date": days, "close": np.linspace(10_000.0, 100.0, len(days))})
        spans = {name: ("2020-01-01", "2026-01-01") for name in panel if name != "dead"}
        spans["dead"] = ("2021-01-01", "2021-06-01")

        def signal_fn(close):
            return pd.Series(close.to_numpy(), index=close.index)

        before = score_cross_section(panel, signal_fn, horizon=1)
        after = score_cross_section(panel, signal_fn, horizon=1, spans=spans)
        self.assertFalse(before["decile_spread"].dropna().empty)
        self.assertFalse(after["decile_spread"].dropna().empty)
        self.assertFalse(np.allclose(
            before["decile_spread"].to_numpy(), after["decile_spread"].to_numpy(), equal_nan=True))
        # With the mask the dead name is out, so dropping it from the panel changes nothing.
        without = dict(panel)
        del without["dead"]
        dropped = score_cross_section(without, signal_fn, horizon=1, spans=spans)
        self.assertTrue(np.allclose(
            after["decile_spread"].to_numpy(), dropped["decile_spread"].to_numpy(), equal_nan=True))

        # The same mask in the sweep path. Three dead names sit above the cut and
        # return the opposite of the live names, so they move the spread before the
        # mask and the cut flags nobody once they are dropped.
        index = days
        cut = pd.DataFrame({name: [50.0] * len(days) for name in panel if name != "dead"}, index=index)
        net = pd.DataFrame(0.01, index=index, columns=list(cut.columns))
        for extra in ("dead", "dead2", "dead3"):
            cut[extra] = 99.0
            net[extra] = -0.5
            spans[extra] = ("2021-01-01", "2021-06-01")
        raw = _spreads(cut, net, {90: 90.0}, "above")
        masked = _spreads(cut, net, {90: 90.0}, "above", spans)
        self.assertTrue(raw[90].notna().any())
        self.assertTrue((raw[90].dropna() < 0).all())
        self.assertTrue(masked[90].isna().all())


if __name__ == "__main__":
    unittest.main()
