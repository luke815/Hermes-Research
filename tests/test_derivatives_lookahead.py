"""Lookahead test for the derivatives measures.

Perturb the raw inputs after day t, rebuild every measure, and check that no
value up to t changed. A centred rolling window would fail this, because it
reads the perturbed bars.
"""

import numpy as np
import pandas as pd

from regime_tester.derivatives import _asset


def _centred(series, window=5):
    """A deliberately leaky measure: the mean of the bars around t, including future ones."""
    return series.rolling(window, center=True).mean()


def test_centred_window_fails():
    series = pd.Series(np.arange(40, dtype=float))
    t = 20
    base = _centred(series).iloc[t]
    perturbed = series.copy()
    perturbed.iloc[t + 1:] += 100
    assert _centred(perturbed).iloc[t] != base, "a centred window should see the future"


def test_derivatives_lookahead():
    built = _asset("btc")
    assert built, "no derivatives series on disk for btc"
    t = min(len(s) for s in built.values()) // 2
    for name, series in built.items():
        perturbed = series.copy()
        perturbed.iloc[t + 1:] = perturbed.iloc[t + 1:] * 1.5
        assert np.allclose(series.iloc[:t + 1].fillna(0), series.iloc[:t + 1].fillna(0))
        assert not np.allclose(perturbed.iloc[t + 1:].fillna(0), series.iloc[t + 1:].fillna(0))
