"""Loader, no-look-ahead, and scoring checks. Run: python3 -m unittest discover -s tests"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from regime_tester.load import load_inbox
from regime_tester.regimes import forward_return, make_features, walk_forward_quintile
from regime_tester.score import combinations, isolation


def _series(n: int, seed: int = 0) -> pd.Series:
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(size=n).cumsum() + 100, index=idx)


class NoLookAhead(unittest.TestCase):
    def test_feature_ignores_future(self):
        full = _series(400)
        features_full = make_features(full)
        # Chopping the tail must not change features before the chop.
        cut = 300
        features_cut = make_features(full.iloc[:cut])
        pd.testing.assert_series_equal(
            features_full["z"].iloc[:cut].dropna(),
            features_cut["z"].dropna(),
        )

    def test_quintile_ignores_own_value(self):
        series = _series(300, seed=1)
        labels = walk_forward_quintile(series)
        # Shifting the current value must not move its own label.
        bumped = series.copy()
        bumped.iloc[200] += 10_000
        relabelled = walk_forward_quintile(bumped)
        self.assertEqual(labels.iloc[200], relabelled.iloc[200])

    def test_forward_return_is_actually_forward(self):
        price = _series(50, seed=2)
        fwd = forward_return(price, 5)
        self.assertTrue(fwd.iloc[-5:].isna().all())
        self.assertAlmostEqual(fwd.iloc[0], price.iloc[5] / price.iloc[0] - 1)


class Loader(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_laevitas_json_joins_price_file(self):
        idx = pd.date_range("2024-06-01", periods=100, freq="h", tz="UTC")
        items = [{"date": int(t.timestamp() * 1000), "funding": 0.0001 * i, "apr": 0.01 * i} for i, t in enumerate(idx)]
        (self.tmp / "funding_btc.json").write_text(json.dumps({"data": {"items": items}}))
        pd.DataFrame({"date": idx, "price": np.linspace(60000, 62000, 100)}).to_csv(self.tmp / "btc_price.csv", index=False)

        panels = load_inbox(self.tmp)
        self.assertIn("BTC", panels)
        panel = panels["BTC"]
        self.assertIn("price", panel.columns)
        self.assertIn("funding", panel.columns)
        self.assertEqual(len(panel), 100)

    def test_tenor_columns_get_namespaced(self):
        idx = pd.date_range("2024-06-01", periods=30, freq="D", tz="UTC")
        pd.DataFrame({"date": idx, "price": 100, "7": 40, "30": 35}).to_csv(self.tmp / "atm_iv_eth.csv", index=False)
        panel = load_inbox(self.tmp)["ETH"]
        self.assertIn("atm_iv_eth_7", panel.columns)
        self.assertIn("atm_iv_eth_30", panel.columns)

    def test_missing_price_raises(self):
        idx = pd.date_range("2024-06-01", periods=10, freq="h", tz="UTC")
        pd.DataFrame({"date": idx, "funding": 0.001}).to_csv(self.tmp / "funding_sol.csv", index=False)
        with self.assertRaises(ValueError):
            load_inbox(self.tmp)


class Scoring(unittest.TestCase):
    def test_planted_signal_is_found(self):
        n = 2000
        idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
        rng = np.random.default_rng(3)
        # A slow regime, the shape funding or IV actually has. White noise
        # would not survive the trailing z-score, so it is the wrong fixture.
        regime = pd.Series(rng.normal(size=n), index=idx).rolling(100, min_periods=1).mean()
        drift = 0.0004 * regime.shift(1).fillna(0)
        returns = drift.to_numpy() + rng.normal(scale=0.001, size=n)
        price = pd.Series(100 * (1 + returns).cumprod(), index=idx)
        noise = pd.Series(rng.normal(size=n), index=idx)
        panel = pd.DataFrame({"price": price, "real": regime, "noise": noise})

        alone = isolation(panel, horizon=24)
        real_t = alone[alone["indicator"] == "real"]["tstat"].abs().max()
        noise_t = alone[alone["indicator"] == "noise"]["tstat"].abs().max()
        self.assertGreater(real_t, 4)
        self.assertGreater(real_t, noise_t)

    def test_combinations_return_rows(self):
        n = 1200
        idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
        rng = np.random.default_rng(4)
        a = pd.Series(rng.normal(size=n), index=idx).rolling(80, min_periods=1).mean()
        b = a + rng.normal(scale=0.05, size=n)
        drift = 0.0003 * a.shift(1).fillna(0)
        price = pd.Series(50 * (1 + drift.to_numpy() + rng.normal(scale=0.001, size=n)).cumprod(), index=idx)
        panel = pd.DataFrame({"price": price, "a": a, "b": b})
        combos = combinations(panel, horizon=24, max_legs=2, top_n=2)
        self.assertFalse(combos.empty)
        self.assertIn("agreement", combos["kind"].values)


if __name__ == "__main__":
    unittest.main()
