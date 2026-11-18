"""Three fixed periods and a non-overlapping spread.

The periods are fixed in the research program and are never moved:
train through 2024-06-30, validation from 2024-07-01 through 2025-12-31,
and test from 2026-01-01 onward. The test period grows every day and is
never used to choose a parameter.

The spread is the top quintile minus the bottom quintile of a factor,
with cut-offs taken from the expanding distribution of values strictly
before the bar. t-stats use every h-th bar, so a 10-day forward return
is counted once instead of ten times.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

PERIODS = (
    ("train", None, "2024-06-30"),
    ("validation", "2024-07-01", "2025-12-31"),
    ("test", "2026-01-01", None),
)

MIN_HISTORY = 60


def assign_period(index: pd.DatetimeIndex) -> pd.Series:
    """Name the period each bar falls in. Bars before the first period are
    unnamed and are dropped by the caller."""
    dates = pd.Series(index.tz_convert("UTC").normalize() if index.tz is not None else index.normalize(), index=index)
    out = pd.Series(pd.NA, index=index, dtype="object")
    for name, start, end in PERIODS:
        mask = pd.Series(True, index=index)
        if start is not None:
            mask &= dates >= pd.Timestamp(start, tz="UTC")
        if end is not None:
            mask &= dates <= pd.Timestamp(end, tz="UTC")
        out[mask] = name
    return out.rename("period")


def quintile_edges(factor: pd.Series, low: float = 0.2, high: float = 0.8,
                   min_history: int = MIN_HISTORY) -> pd.DataFrame:
    """Expanding cut-offs from values strictly before the bar."""
    past = factor.expanding(min_periods=min_history)
    return pd.DataFrame({
        "lo": past.quantile(low).shift(1),
        "hi": past.quantile(high).shift(1),
    })


def _spread(top: np.ndarray, bot: np.ndarray) -> dict:
    """Top minus bottom, with an unequal-variance t-stat. Either side empty
    returns a row of NaNs so the absence is visible rather than dropped."""
    if len(top) == 0 or len(bot) == 0:
        return {"spread": float("nan"), "t": float("nan"), "n_top": int(len(top)),
                "n_bot": int(len(bot)), "n": 0, "top_mean": float("nan"), "bot_mean": float("nan")}
    gap = float(top.mean() - bot.mean())
    se = np.sqrt(top.var(ddof=1) / len(top) + bot.var(ddof=1) / len(bot)) if len(top) > 1 and len(bot) > 1 else np.nan
    return {
        "spread": gap,
        "t": float(gap / se) if se and not np.isnan(se) else float("nan"),
        "n_top": int(len(top)),
        "n_bot": int(len(bot)),
        "n": int(min(len(top), len(bot))),
        "top_mean": float(top.mean()),
        "bot_mean": float(bot.mean()),
    }


def nonoverlapping_spread(factor: pd.Series, forward: pd.Series, horizon: int,
                          low: float = 0.2, high: float = 0.8,
                          min_history: int = MIN_HISTORY) -> dict:
    """Spread on every h-th bar, so forward windows do not share days.

    The stride starts at the first bar that has both a cut-off and a closed
    window, and the same bars are used for every period and every year.
    """
    edges = quintile_edges(factor, low, high, min_history)
    both = pd.concat([factor.rename("x"), forward.rename("f"), edges], axis=1).dropna()
    if both.empty:
        return _spread(np.array([]), np.array([]))
    stride = both.iloc[::horizon]
    top = stride.loc[stride["x"] > stride["hi"], "f"].to_numpy()
    bot = stride.loc[stride["x"] < stride["lo"], "f"].to_numpy()
    return _spread(top, bot)


def spread_by_period(factor: pd.Series, forward: pd.Series, horizon: int,
                     low: float = 0.2, high: float = 0.8) -> dict:
    """The same spread inside each fixed period, on the non-overlapping bars."""
    edges = quintile_edges(factor, low, high)
    period = assign_period(factor.index)
    both = pd.concat([factor.rename("x"), forward.rename("f"), edges, period], axis=1).dropna()
    stride = both.iloc[::horizon] if not both.empty else both
    out = {}
    for name, _, _ in PERIODS:
        part = stride[stride["period"] == name]
        top = part.loc[part["x"] > part["hi"], "f"].to_numpy()
        bot = part.loc[part["x"] < part["lo"], "f"].to_numpy()
        out[name] = _spread(top, bot)
    return out


def spread_by_year(factor: pd.Series, forward: pd.Series, horizon: int,
                   low: float = 0.2, high: float = 0.8) -> list[dict]:
    """The same spread per calendar year, with the independent count per year."""
    edges = quintile_edges(factor, low, high)
    both = pd.concat([factor.rename("x"), forward.rename("f"), edges], axis=1).dropna()
    stride = both.iloc[::horizon] if not both.empty else both
    rows = []
    if stride.empty:
        return rows
    years = sorted(stride.index.year.unique())
    for year in years:
        part = stride[stride.index.year == year]
        top = part.loc[part["x"] > part["hi"], "f"].to_numpy()
        bot = part.loc[part["x"] < part["lo"], "f"].to_numpy()
        row = _spread(top, bot)
        row["year"] = int(year)
        rows.append(row)
    return rows
