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
    """A small store: one raw series per input the measures read."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    dvol = 40 + np.cumsum(rng.normal(0, 1, n))
    rv7 = 30 + np.cumsum(rng.normal(0, 0.5, n))
    rv30 = 35 + np.cumsum(rng.normal(0, 0.4, n))
    atm7 = 50 + np.cumsum(rng.normal(0, 0.6, n))
    atm90 = 55 + np.cumsum(rng.normal(0, 0.6, n))
    skew = rng.normal(-2, 1, n)
    rr = rng.normal(0, 1, n)
    basis = rng.normal(0.01, 0.005, n)
    funding = rng.normal(0.0001, 0.0003, n)
    files = {
        "dvol_btc_a.json": [{"date": int(s.timestamp() * 1000), "dvol": float(v)} for s, v in zip(idx, dvol)],
        "rv_btc_a.json": [{"date": int(s.timestamp() * 1000), "7": float(a), "30": float(b)} for s, a, b in zip(idx, rv7, rv30)],
        "atmiv_btc_a.json": [{"date": int(s.timestamp() * 1000), "7": float(a), "90": float(b)} for s, a, b in zip(idx, atm7, atm90)],
        "skew_btc_a.json": [{"date": int(s.timestamp() * 1000), "7": float(v), "30": float(v), "90": float(v)} for s, v in zip(idx, skew)],
        "rr_btc_a.json": [{"date": int(s.timestamp() * 1000), "30": float(v)} for s, v in zip(idx, rr)],
        "basis_btc_a.json": [{"date": int(s.timestamp() * 1000), "BINANCE": float(v)} for s, v in zip(idx, basis)],
        "oiw_funding_btc_a.json": [{"date": int(s.timestamp() * 1000), "funding": float(v), "funding_c": float(v), "funding_u": float(v + 0.0001)} for s, v in zip(idx, funding)],
    }
    for name, rows in files.items():
        (directory / name).write_text(json.dumps(rows))
    return idx


def _perturb(src, dest, cutoff):
    """Copy the store and scale every row dated after cutoff by 1.5."""
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    for path in dest.glob("*.json"):
        rows = json.loads(path.read_text())
        for row in rows:
            if pd.Timestamp(row["date"], unit="ms", tz="UTC") <= cutoff:
                continue
            for key, value in list(row.items()):
                if key != "date" and isinstance(value, (int, float)):
                    row[key] = value * 1.5
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
        """Scaling every raw row after t must leave every measure up to t in place."""
        src = Path(self.tmp.name) / "src"
        src.mkdir()
        idx = _plant(src)
        cutoff = idx[len(idx) // 2]
        dest = Path(self.tmp.name) / "dest"
        _perturb(src, dest, cutoff)

        derivatives.RAW = src
        base = market_measures()
        self.assertGreater(len(base.columns), 5, "the planted store built no measures")
        derivatives.RAW = dest
        again = market_measures()
        self.assertTrue(
            _unchanged(base, again, cutoff),
            "a measure moved at or before t when only later raw rows changed",
        )


if __name__ == "__main__":
    unittest.main()
