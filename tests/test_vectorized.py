"""The vectorized scorer matches the per-cell scorer, and does not look ahead.

The gate in research/SWEEP_V2.md section 1: on 50 randomly chosen cells the
vectorized statistics match the per-cell scorer to six decimals, and perturbing
every price after day t leaves the signal at t unchanged.
"""

import numpy as np
import pandas as pd

from regime_tester.cross_section import decile_spread, rank_ic
from regime_tester.vectorized import (
    decile_spread_matrix, forward_returns, lookahead_holds, rank_ic_matrix,
    return_stats, signal_matrix, transform_matrix,
)


def _close(seed=0, names=40, days=400):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2022-01-01", periods=days, freq="D").strftime("%Y-%m-%d")
    data = {f"n{i}": 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.02, days)))
            for i in range(names)}
    return pd.DataFrame(data, index=dates)


def _scale(transform):
    if transform.startswith("z_"):
        return "zscore"
    if transform.startswith("chg_"):
        return "cross_section"
    return "percentile"


def _cells(seed=1, n=50):
    rng = np.random.default_rng(seed)
    transforms = ["pct_252", "z_30", "z_90", "chg_3", "chg_7", "chg_30"]
    thresholds = [5, 10, 20, 80, 90, 95]
    horizons = [1, 3, 10]
    for _ in range(n):
        yield (transforms[rng.integers(len(transforms))],
               int(thresholds[rng.integers(len(thresholds))]),
               int(horizons[rng.integers(len(horizons))]))


def _per_cell(transformed, forward):
    """The per-cell scorer's rank IC and decile spread, date by date."""
    ic, spread = [], []
    for date in transformed.index:
        ic.append(rank_ic(transformed.loc[date], forward.loc[date]))
        spread.append(decile_spread(transformed.loc[date], forward.loc[date]))
    return np.array(ic, dtype=float), np.array(spread, dtype=float)


def test_matches_per_cell_scorer_to_six_decimals():
    close = _close()
    returns = forward_returns(close, [1, 3, 10])
    measure = close.pct_change(10)
    seen = 0
    worst = 0.0
    for transform, threshold, horizon in _cells():
        direction = "below" if threshold <= 20 else "above"
        transformed = transform_matrix(measure, transform).shift(1)
        forward = returns[horizon]
        # Rank IC and decile spread are defined on the transform, not on the
        # threshold cut. The cut is checked separately: it must flag some names
        # and leave others, or the cell has no spread to measure.
        vector_ic = rank_ic_matrix(transformed, forward).to_numpy()
        vector_spread = decile_spread_matrix(transformed, forward).to_numpy()
        cell_ic, cell_spread = _per_cell(transformed, forward)
        for got, ref in ((vector_ic, cell_ic), (vector_spread, cell_spread)):
            both = ~(np.isnan(got) | np.isnan(ref))
            assert np.array_equal(np.isnan(got), np.isnan(ref))
            if both.any():
                gap = float(np.max(np.abs(got[both] - ref[both])))
                worst = max(worst, gap)
                assert gap < 1e-6
        flagged = signal_matrix(transformed, threshold, direction, _scale(transform))
        assert flagged.notna().any().any()
        stats = return_stats(flagged, forward, horizon)
        assert stats["n_independent"] > 0
        seen += 1
    assert seen == 50
    assert worst < 1e-6


def test_lookahead_holds_for_every_transform():
    close = _close(seed=2, names=8, days=200)
    t = len(close) // 2
    for name in ("raw", "pct_252", "z_30", "z_90", "chg_7", "persistence", "acceleration"):
        def measure_fn(frame, name=name):
            return transform_matrix(frame, name).shift(1)
        assert lookahead_holds(measure_fn, close, t), name


def test_early_bars_stay_empty():
    close = _close(seed=3, names=4, days=120)
    for name, first in (("z_30", 29), ("z_90", 89), ("pct_252", 29), ("chg_7", 7)):
        got = transform_matrix(close, name)
        assert got.iloc[:first].isna().all().all(), name
        assert got.iloc[first:].notna().any().any(), name
