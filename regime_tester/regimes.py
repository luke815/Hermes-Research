"""Causal regime features and walk-forward quintile labels.

Every feature at bar t is computed from data strictly before t. Quintile
edges are the expanding distribution of past feature values, so a bar is
never labelled using its own value or anything after it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MIN_HISTORY = 48  # bars before a feature or regime label is trusted


def make_features(series: pd.Series, window: int = 168) -> pd.DataFrame:
    """Trailing z-score, change, and percentile rank. All shifted by 1."""
    past = series.shift(1)
    mean = past.rolling(window, min_periods=MIN_HISTORY).mean()
    std = past.rolling(window, min_periods=MIN_HISTORY).std()
    z = (past - mean) / std.replace(0, np.nan)
    change = past.pct_change(window)
    rank = past.rolling(window, min_periods=MIN_HISTORY).rank(pct=True)
    return pd.DataFrame({"z": z, "chg": change, "rank": rank})


def walk_forward_quintile(feature: pd.Series, min_history: int = MIN_HISTORY) -> pd.Series:
    """Label each bar 0-4 by where it sits in the expanding past distribution.

    Edges come from `feature` values up to but not including the current bar.
    Implemented with a single expanding rank, which is equivalent and avoids
    refitting per row.
    """
    past = feature.shift(1)
    expanding_rank = past.expanding(min_periods=min_history).rank(pct=True)
    labels = np.floor(expanding_rank * 5).clip(0, 4)
    return labels.rename("regime")


def forward_return(price: pd.Series, horizon: int) -> pd.Series:
    """Return from bar t to bar t+horizon.

    This is the move that happens *after* bar t prints, which is what a signal
    known at t could have predicted. NaN for the last `horizon` bars, where the
    outcome is not yet known.
    """
    return price.shift(-horizon) / price - 1
