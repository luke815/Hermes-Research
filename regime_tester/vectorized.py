"""Vectorized cross-sectional scorer, the S7 module.

The per-cell scorer recomputes the indicator for every cell. This one computes
the indicator matrix once per measure and evaluates every transform, threshold
and target of that measure as matrix operations. The correctness gate requires
its statistics to match the per-cell scorer to six decimals on a sample of
cells, and the lookahead test to pass, before it replaces that scorer.
"""

import hashlib
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "panel_xs_cache")


def load_close_matrix(panel_dir, names=None):
    """Dates by names close matrix, and the panel hash the cache keys on."""
    files = sorted(f for f in os.listdir(panel_dir) if f.endswith(".csv"))
    frames = {}
    for name in files:
        if names and name not in names:
            continue
        frame = pd.read_csv(os.path.join(panel_dir, name), usecols=["date", "close"])
        frames[name.replace(".csv", "")] = frame.set_index("date")["close"].astype(float)
    matrix = pd.DataFrame(frames).sort_index()
    digest = hashlib.sha256(pd.util.hash_pandas_object(matrix).values.tobytes()).hexdigest()[:16]
    return matrix, digest


def forward_returns(close, horizons):
    """R_h matrices, computed once and reused across every cell."""
    return {h: close.shift(-h) / close - 1 for h in horizons}


def rank_ic_matrix(signal, forward):
    """Spearman rank IC per date, across the names present that date."""
    both = signal.notna() & forward.notna()
    s = signal.where(both).rank(axis=1)
    f = forward.where(both).rank(axis=1)
    s = s.sub(s.mean(axis=1), axis=0)
    f = f.sub(f.mean(axis=1), axis=0)
    num = (s * f).sum(axis=1)
    den = np.sqrt((s ** 2).sum(axis=1) * (f ** 2).sum(axis=1))
    out = num / den.replace(0, np.nan)
    out[both.sum(axis=1) < 10] = np.nan
    return out


def decile_spread_matrix(signal, forward):
    """Top decile mean minus bottom decile mean, per date, in percent."""
    both = signal.notna() & forward.notna()
    ranks = signal.where(both).rank(axis=1, pct=True)
    top = forward.where(ranks >= 0.9)
    bottom = forward.where(ranks <= 0.1)
    spread = (top.mean(axis=1) - bottom.mean(axis=1)) * 100
    spread[both.sum(axis=1) < 20] = np.nan
    return spread
