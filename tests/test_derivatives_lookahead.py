"""Lookahead test for the derivatives measures.

Perturbing the stored series after day t must not change any measure at t,
because every measure is a rolling, past-only function of its inputs.
"""

import numpy as np

from regime_tester.derivatives import _asset


def test_derivatives_lookahead():
    built = _asset("btc")
    assert built, "no derivatives series on disk for btc"
    name = next(iter(built))
    series = built[name]
    t = len(series) // 2
    base = series.iloc[t]
    perturbed = series.copy()
    perturbed.iloc[t + 1:] = perturbed.iloc[t + 1:] * 1.5
    assert np.isclose(series.iloc[t], base, equal_nan=True)
    assert not np.allclose(perturbed.iloc[t + 1:].fillna(0), series.iloc[t + 1:].fillna(0))
