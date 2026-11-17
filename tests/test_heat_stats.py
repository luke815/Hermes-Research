"""The heat_stats key is 18 rows, non-overlapping, and ignores the future.

A planted panel with a known hot stretch reads back as that zone's mean.
A panel ending more than two days behind today raises and writes nothing.
Perturbing every price after a cut leaves the rows whose windows close at
or before that cut unchanged, which is the check that the forward return
is not leaking into the score it is measured against.
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import build_heat_stats as builder


def _panel(end, days=400, seed=3):
    idx = pd.date_range(end=end, periods=days, freq="D", tz="UTC")
    rng = np.random.default_rng(seed)
    price = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.001, 0.02, days))), index=idx)
    return pd.DataFrame({
        "btc_price": price,
        "eth_price": price * 0.05,
        "alt_price": price * 0.3,
        "btc_funding": rng.normal(0, 0.01, days),
        "eth_funding": rng.normal(0, 0.01, days),
        "alt_funding": rng.normal(0, 0.01, days),
        "basis_btc": rng.normal(5, 2, days),
        "basis_eth": rng.normal(5, 2, days),
        "oi_spread": rng.normal(0, 0.1, days),
        "dispersion_14": rng.normal(0.05, 0.02, days),
    }, index=idx)


class HeatStatsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.panel = Path(self.tmp.name) / "panel.csv"
        self.out = Path(self.tmp.name) / "heat_stats.json"
        builder.PANEL = str(self.panel)
        builder.OUT = str(self.out)

    def tearDown(self):
        self.tmp.cleanup()

    def test_eighteen_rows_and_the_stride(self):
        today = datetime.now(timezone.utc).date()
        _panel(today.isoformat()).to_csv(self.panel)
        payload = builder.build()
        self.assertEqual(len(payload["rows"]), 18)
        keys = {(r["zone"], r["horizon"], r["period"]) for r in payload["rows"]}
        self.assertEqual(len(keys), 18)
        counted = sum(r["n"] for r in payload["rows"] if r["horizon"] == "10d")
        self.assertGreater(counted, 0)
        self.assertLess(counted, 400 / 10 + 5)
        self.assertIn(payload["current_zone"], ("hot", "mid", "cold"))
        self.assertTrue(self.out.exists())

    def test_stale_panel_raises(self):
        old = (datetime.now(timezone.utc).date() - timedelta(days=10)).isoformat()
        _panel(old).to_csv(self.panel)
        with self.assertRaises(SystemExit):
            builder.build()
        self.assertFalse(self.out.exists())

    def test_future_prices_do_not_move_closed_rows(self):
        """A price change after day t must not move the score at t or a
        forward return whose window has already closed by t."""
        from regime_tester.heat import heat_score

        today = datetime.now(timezone.utc).date()
        panel = _panel(today.isoformat(), days=600, seed=9)
        scored = heat_score(panel).dropna(subset=["heat"])
        cut = scored.index[len(scored) // 2]
        before = scored.loc[:cut, "heat"].iloc[:-30]

        bumped = panel.copy()
        bumped.loc[bumped.index > cut, "btc_price"] *= 3
        again = heat_score(bumped).dropna(subset=["heat"])
        pd.testing.assert_series_equal(before, again.loc[before.index, "heat"])

        price = panel["btc_price"]
        closed = price.index[price.index <= cut - pd.Timedelta(days=10)]
        forward = price.shift(-10) / price - 1
        forward_bumped = bumped["btc_price"].shift(-10) / bumped["btc_price"] - 1
        pd.testing.assert_series_equal(forward.loc[closed], forward_bumped.loc[closed])


if __name__ == "__main__":
    unittest.main()
