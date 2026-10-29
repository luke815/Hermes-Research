"""Technical factors, each trailing only, for the admission test.

Nothing here is assumed to predict. Each one is a candidate that has to widen
the out-of-sample gap before it joins a model. The functions return a series
aligned to the price index, using only data available at each bar.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _zscore(series: pd.Series, window: int) -> pd.Series:
    past = series.shift(1)
    mean = past.rolling(window, min_periods=window // 2).mean()
    std = past.rolling(window, min_periods=window // 2).std().replace(0, np.nan)
    return (past - mean) / std


def moving_average_structure(price: pd.Series) -> pd.DataFrame:
    """Where price sits relative to its averages, and whether the averages stack."""
    out = pd.DataFrame(index=price.index)
    for window in (20, 50, 200):
        average = price.rolling(window, min_periods=window // 2).mean()
        out[f"dist_ma{window}"] = _zscore(price / average - 1, 120)
        out[f"slope_ma{window}"] = _zscore(average.pct_change(10), 120)
    ma20 = price.rolling(20).mean()
    ma50 = price.rolling(50).mean()
    ma200 = price.rolling(200).mean()
    # 1 when the averages are stacked bullish, -1 when stacked bearish
    out["ma_stack"] = np.sign(ma20 - ma50) + np.sign(ma50 - ma200)
    out["ma_stack"] = out["ma_stack"].shift(1)
    return out


def range_breakout(price: pd.Series, window: int = 20) -> pd.Series:
    """Distance beyond the prior window's high or low. Positive is an upside break."""
    prior_high = price.rolling(window).max().shift(1)
    prior_low = price.rolling(window).min().shift(1)
    above = (price - prior_high) / prior_high
    below = (price - prior_low) / prior_low
    breakout = pd.Series(np.where(price > prior_high, above, np.where(price < prior_low, below, 0.0)), index=price.index)
    return breakout.shift(1).rename(f"donchian_{window}")


def rsi(price: pd.Series, window: int = 14) -> pd.Series:
    delta = price.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    value = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    return _zscore(value, 120).rename(f"rsi_{window}")


def bollinger_width(price: pd.Series, window: int = 20) -> pd.Series:
    """Band width as a volatility-compression measure. Low means a squeeze."""
    mean = price.rolling(window).mean()
    std = price.rolling(window).std()
    width = (4 * std) / mean
    return _zscore(width, 120).rename("bollinger_width")


def atr_regime(price: pd.Series, window: int = 14) -> pd.Series:
    change = price.diff().abs()
    atr = change.rolling(window).mean() / price
    return _zscore(atr, 120).rename("atr_regime")


def build_ta(price: pd.Series) -> pd.DataFrame:
    """Every TA candidate for one asset, trailing only."""
    parts = [
        moving_average_structure(price),
        range_breakout(price, 20),
        range_breakout(price, 55),
        rsi(price, 14),
        bollinger_width(price),
        atr_regime(price),
    ]
    return pd.concat(parts, axis=1)
