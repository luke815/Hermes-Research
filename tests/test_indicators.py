"""Tests for the indicator library.

A planted pattern must come out as that pattern, and a value at bar t must not
change when every price after t is perturbed. The second check is the one that
catches a lookahead.
"""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from regime_tester.indicators import (  # noqa: E402
    LIBRARY_VERSION, META, indicators, metadata, td_sequential,
)


def frame(n=400, seed=7):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.02, n)))
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    return pd.DataFrame({
        "open": close * (1 + rng.normal(0, 0.001, n)),
        "high": close * (1 + np.abs(rng.normal(0, 0.01, n))),
        "low": close * (1 - np.abs(rng.normal(0, 0.01, n))),
        "close": close,
        "volume": rng.uniform(1e6, 5e6, n),
        "funding": rng.normal(0.0001, 0.0003, n),
        "oi": 1e8 + np.cumsum(rng.normal(0, 1e6, n)),
        "liq": np.abs(rng.normal(1e6, 5e5, n)),
    }, index=idx)


class LibraryTests(unittest.TestCase):
    def test_version_and_metadata_cover_every_column(self):
        self.assertEqual(LIBRARY_VERSION, "1.0.0")
        out = indicators(frame())
        self.assertTrue(set(out.columns) <= set(META))
        self.assertGreater(len(out.columns), 30)
        table = metadata()
        self.assertEqual(len(table), len(META))
        self.assertTrue(set(table["kind"]) <= {"level", "oscillator", "flag", "count"})

    def test_no_lookahead(self):
        base = frame()
        out = indicators(base)
        t = len(base) // 2
        perturbed = base.copy()
        perturbed.iloc[t + 1:] *= 3
        again = indicators(perturbed)
        for col in out.columns:
            before = out[col].iloc[:t + 1].to_numpy()
            after = again[col].iloc[:t + 1].to_numpy()
            both_nan = np.isnan(before) & np.isnan(after)
            self.assertTrue(
                np.allclose(before[~both_nan], after[~both_nan], equal_nan=True),
                f"{col} at bar {t} changed when later prices were perturbed",
            )

    def test_td_setup_counts_a_planted_run(self):
        close = pd.Series([10, 10, 10, 10, 10] + [11, 12, 13, 14, 15, 16, 17, 18, 19])
        setup, _ = td_sequential(close, None, None)
        # closes 11 through 19 are each above the close four bars earlier, so the
        # ninth of them completes a sell setup
        self.assertEqual(setup.iloc[-1], 9)

    def test_td_buy_setup_is_negative(self):
        close = pd.Series([20, 20, 20, 20, 20] + [19, 18, 17, 16, 15, 14, 13, 12, 11])
        setup, _ = td_sequential(close, None, None)
        self.assertEqual(setup.iloc[-1], -9)

    def test_missing_inputs_drop_the_column(self):
        bare = frame()[["close"]]
        out = indicators(bare)
        self.assertIn("rsi_14", out.columns)
        self.assertNotIn("atr_14", out.columns)
        self.assertNotIn("cmf_20", out.columns)

    def test_pi_cycle_needs_350_bars(self):
        out = indicators(frame(360))
        self.assertTrue(out["pi_cycle"].iloc[:349].isna().all())
        self.assertTrue(out["pi_cycle"].iloc[349:].notna().any())

    def test_mayer_multiple_is_price_over_200_average(self):
        f = frame()
        out = indicators(f)
        expected = f["close"] / f["close"].rolling(200).mean()
        self.assertTrue(np.allclose(out["mayer_multiple"].iloc[199:], expected.iloc[199:]))

    def test_funding_persistence_counts_a_hot_run(self):
        f = frame()
        f.loc[f.index[-5]:, "funding"] = 0.01
        out = indicators(f)
        self.assertGreater(out["funding_persist_high"].iloc[-1], 0)

    def test_liq_cascade_flags_an_extreme(self):
        f = frame()
        f.loc[f.index[-1], "liq"] = f["liq"].max() * 100
        out = indicators(f)
        self.assertEqual(out["liq_cascade"].iloc[-1], 1.0)


if __name__ == "__main__":
    unittest.main()
