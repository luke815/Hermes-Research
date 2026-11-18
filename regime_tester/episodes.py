"""Top and bottom events, and the episodes they form.

A top event T(h, x) is true on day t when the lowest close in the next h
days is at least x percent below the close on day t. A bottom event
B(h, x, y) is true when the highest close in the next h days is at least
x percent above today's close and no close in between falls more than y
percent below it. Both look forward and are labels, never features.

An episode is a run of consecutive days carrying the same label, counted
as one. The episode count is the honest sample size; the day count is
reported beside it so the clustering is visible.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Primary definitions, plus the neighbours the research program names.
TOPS = ((30, 0.15), (20, 0.10), (60, 0.25))
BOTTOMS = ((30, 0.15, 0.07), (60, 0.30, 0.10))


def forward_window(close: pd.Series, horizon: int) -> np.ndarray:
    """Close[t+1 .. t+h] as a (n, h) array. Rows whose window is not closed
    are NaN, so a label can never be true on a day whose future is unknown."""
    values = close.to_numpy(dtype=float)
    n = len(values)
    out = np.full((n, horizon), np.nan)
    if n == 0:
        return out
    with np.errstate(all="ignore"):
        for k in range(1, horizon + 1):
            out[: n - k, k - 1] = values[k:]
    return out


def top_event(close: pd.Series, horizon: int, drawdown: float) -> pd.Series:
    """T(h, x): the lowest close within the next h days is at least x below today."""
    window = forward_window(close, horizon)
    closed = ~np.isnan(window).any(axis=1)
    trough = np.where(closed, np.nanmin(np.where(closed[:, None], window, np.inf), axis=1), np.nan)
    label = closed & (trough <= close.to_numpy(dtype=float) * (1 - drawdown))
    return pd.Series(label, index=close.index, name=f"top_{horizon}_{int(drawdown * 100)}")


def bottom_event(close: pd.Series, horizon: int, rally: float, giveback: float) -> pd.Series:
    """B(h, x, y): the highest close within h days is at least x above today,
    and no close in the window is more than y below today."""
    window = forward_window(close, horizon)
    closed = ~np.isnan(window).any(axis=1)
    finite = np.where(closed[:, None], window, np.inf)
    peak = np.where(closed, np.nanmax(np.where(closed[:, None], window, -np.inf), axis=1), np.nan)
    trough = np.where(closed, np.nanmin(finite, axis=1), np.nan)
    price = close.to_numpy(dtype=float)
    label = closed & (peak >= price * (1 + rally)) & (trough >= price * (1 - giveback))
    return pd.Series(label, index=close.index, name=f"bottom_{horizon}_{int(rally * 100)}_{int(giveback * 100)}")


def episodes(label: pd.Series) -> pd.Series:
    """Number each run of consecutive true days, starting at 1. False days
    and days whose label is unknown are 0. A gap of one day starts a new run."""
    true = label.fillna(False).astype(bool)
    starts = true & ~true.shift(1, fill_value=False)
    ids = starts.cumsum().where(true, 0)
    return ids.rename(label.name)


def episode_table(label: pd.Series) -> pd.DataFrame:
    """One row per episode: start, end, length in days."""
    ids = episodes(label)
    rows = []
    for episode_id, group in ids[ids > 0].groupby(ids[ids > 0]):
        rows.append({
            "episode": int(episode_id),
            "start": group.index.min(),
            "end": group.index.max(),
            "days": int(len(group)),
        })
    return pd.DataFrame(rows, columns=["episode", "start", "end", "days"])


def base_rates(label: pd.Series, period: pd.Series) -> dict:
    """Share of days labelled true, and the episode count, per period and year.

    Days whose window has not closed are excluded from the denominator, so a
    base rate is the share of decided days, not the share of all days.
    """
    decided = label.notna()
    ids = episodes(label)
    frame = pd.DataFrame({
        "label": label.astype("boolean"),
        "period": period,
        "year": label.index.year,
        "episode": ids,
    })
    frame = frame[decided]

    def block(group: pd.DataFrame) -> dict:
        days = int(len(group))
        true_days = int(group["label"].sum())
        n_episodes = int(group.loc[group["label"], "episode"].nunique())
        return {
            "days": days,
            "true_days": true_days,
            "day_rate": true_days / days if days else float("nan"),
            "episodes": n_episodes,
        }

    by_period = {name: block(group) for name, group in frame.groupby("period") if pd.notna(name)}
    by_year = {int(year): block(group) for year, group in frame.groupby("year")}
    return {"all": block(frame), "by_period": by_period, "by_year": by_year}
