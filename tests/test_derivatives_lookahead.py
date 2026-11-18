"""Lookahead test for the derivatives measures.

Perturb the raw input files after day t, rebuild every measure from the
perturbed copy, and check that no value up to t changed. A measure patched to
a centred window must fail the same harness, so a passing run means the check
can catch a leak.
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from regime_tester import derivatives  # noqa: E402
from regime_tester.derivatives import market_measures  # noqa: E402


def _plant(directory, n=80, seed=3):
    """A small store: one raw series per input the measures read, for both assets."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    for asset, shift in (("btc", 0.0), ("eth", 3.0)):
        dvol = 40 + shift + np.cumsum(rng.normal(0, 1, n))
        rv7 = 30 + np.cumsum(rng.normal(0, 0.5, n))
        rv30 = 35 + np.cumsum(rng.normal(0, 0.4, n))
        atm7 = 50 + np.cumsum(rng.normal(0, 0.6, n))
        atm90 = 55 + np.cumsum(rng.normal(0, 0.6, n))
        skew = rng.normal(-2, 1, n)
        rr = rng.normal(0, 1, n)
        basis = rng.normal(0.01, 0.005, n)
        funding = rng.normal(0.0001, 0.0003, n)
        files = {
            f"dvol_{asset}_a.json": [{"date": int(s.timestamp() * 1000), "dvol": float(v)} for s, v in zip(idx, dvol)],
            f"rv_{asset}_a.json": [{"date": int(s.timestamp() * 1000), "7": float(a), "30": float(b)} for s, a, b in zip(idx, rv7, rv30)],
            f"atmiv_{asset}_a.json": [{"date": int(s.timestamp() * 1000), "7": float(a), "90": float(b)} for s, a, b in zip(idx, atm7, atm90)],
            f"skew_{asset}_a.json": [{"date": int(s.timestamp() * 1000), "7": float(v), "30": float(v), "90": float(v)} for s, v in zip(idx, skew)],
            f"rr_{asset}_a.json": [{"date": int(s.timestamp() * 1000), "30": float(v)} for s, v in zip(idx, rr)],
            f"basis_{asset}_a.json": [{"date": int(s.timestamp() * 1000), "BINANCE": float(v)} for s, v in zip(idx, basis)],
            f"oiw_funding_{asset}_a.json": [{"date": int(s.timestamp() * 1000), "funding": float(v), "funding_c": float(v), "funding_u": float(v + 0.0001)} for s, v in zip(idx, funding)],
        }
        for name, rows in files.items():
            (directory / name).write_text(json.dumps(rows))
    return idx


def _perturb(src, dest, cutoff, seed=11):
    """Copy the store and add seeded noise to every numeric field after cutoff.

    A scale leaves a ratio and a sign flag unchanged, so rv_ratio_7_30 and
    atm_inversion would pass a 1.5x shock even if they read the future. Noise
    moves both.
    """
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    rng = np.random.default_rng(seed)
    for path in sorted(dest.glob("*.json")):
        rows = json.loads(path.read_text())
        for row in rows:
            if pd.Timestamp(row["date"], unit="ms", tz="UTC") <= cutoff:
                continue
            for key, value in list(row.items()):
                if key != "date" and isinstance(value, (int, float)) and not isinstance(value, bool):
                    row[key] = float(value) + float(rng.normal(0, abs(value) * 0.35 + 1.0))
        path.write_text(json.dumps(rows))


def _unchanged(base, again, cutoff):
    """True when every measure agrees on every bar up to and including cutoff."""
    shared = [c for c in base.columns if c in again.columns]
    if not shared:
        return False
    left = base.loc[:cutoff, shared]
    right = again.reindex(base.index).loc[:cutoff, shared]
    return left.fillna(0).equals(right.fillna(0))


class LookaheadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.saved = derivatives.RAW

    def tearDown(self):
        derivatives.RAW = self.saved

    def test_centred_window_fails_the_harness(self):
        """The check must reject a measure that reads the bars around t."""
        src = Path(self.tmp.name) / "src"
        src.mkdir()
        idx = _plant(src)
        cutoff = idx[len(idx) // 2]
        dest = Path(self.tmp.name) / "dest"
        _perturb(src, dest, cutoff)

        def centred():
            raw = derivatives.daily("dvol_btc*.json", lambda r: r.get("dvol"))
            return raw.rolling(5, center=True).mean().to_frame("leaky")

        derivatives.RAW = src
        base = centred()
        derivatives.RAW = dest
        again = centred()
        self.assertFalse(
            _unchanged(base, again, cutoff),
            "a centred window reads the perturbed bars, so the harness must reject it",
        )

    def test_rebuilt_measures_do_not_move(self):
        """Seeded noise after t must leave every measure up to t in place."""
        src = Path(self.tmp.name) / "src"
        src.mkdir()
        idx = _plant(src)
        cutoff = idx[len(idx) // 2]
        dest = Path(self.tmp.name) / "dest"
        _perturb(src, dest, cutoff)

        derivatives.RAW = src
        base = market_measures()
        self.assertGreater(len(base.columns), 5, "the planted store built no measures")
        self.assertIn("rv_ratio_7_30_btc", base.columns)
        self.assertIn("atm_inversion_btc", base.columns)
        self.assertIn("rv_ratio_7_30_eth", base.columns)
        self.assertIn("atm_inversion_eth", base.columns)
        derivatives.RAW = dest
        again = market_measures()
        self.assertTrue(
            _unchanged(base, again, cutoff),
            "a measure moved at or before t when only later raw rows changed",
        )

    def test_seeded_noise_moves_the_scale_free_measures_after_t(self):
        """The same noise must move rv_ratio and atm_inversion after t.

        A 1.5x scale leaves both unchanged, so a harness that only scales
        cannot tell whether those two read the future.
        """
        src = Path(self.tmp.name) / "src2"
        src.mkdir()
        idx = _plant(src, n=80, seed=9)
        cutoff = idx[len(idx) // 2]
        dest = Path(self.tmp.name) / "dest2"
        _perturb(src, dest, cutoff, seed=11)
        derivatives.RAW = src
        base = market_measures()
        derivatives.RAW = dest
        again = market_measures()
        for name in ("rv_ratio_7_30_btc", "atm_inversion_btc", "rv_ratio_7_30_eth", "atm_inversion_eth"):
            after = again[name].loc[again.index > cutoff]
            before = base[name].reindex(after.index)
            self.assertFalse(
                after.fillna(0).equals(before.fillna(0)),
                f"{name} did not move after t, so the perturbation cannot catch a leak in it",
            )


if __name__ == "__main__":
    unittest.main()
