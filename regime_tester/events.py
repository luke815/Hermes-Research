"""Single-factor event test for the positioning family.

A factor is extreme when its trailing 1-year percentile, built from values
strictly before the bar, crosses a fixed cut. The label is an episode start
of T(60, 25%) or B(60, 30%, 10%). A reading counts only when no episode of
that side has already started inside the horizon, so one episode is counted
once. Lift is the share of those readings followed by an episode start
within the horizon, divided by the base rate of such starts.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

HORIZON = 60
YEAR = 365
MIN_HISTORY = 60
PRIMARY_HIGH = 0.90
PRIMARY_LOW = 0.10
NEIGHBOUR_HIGH = (0.85, 0.95)
NEIGHBOUR_LOW = (0.05, 0.15)
STREAK_HIGH = 0.80
STREAK_LOW = 0.20
STREAK_DAYS = 5
STREAK_NEIGHBOURS = (3, 7)
BOOTSTRAP_DRAWS = 2000
BOOTSTRAP_SEED = 60


def rolling_percentile(series: pd.Series, window: int = YEAR,
                       min_history: int = MIN_HISTORY) -> pd.Series:
    """Percentile of the prior bar inside the window ending at the prior bar.

    Bar t is excluded twice: the window is shifted one, and the value being
    ranked is the prior bar, so nothing known only at the close of t enters.
    """
    past = series.shift(1)
    rank = past.rolling(window, min_periods=min_history).rank(pct=True)
    return rank.rename(series.name)


def streak(high: pd.Series, days: int) -> pd.Series:
    """True when the last `days` bars, ending at the prior bar, were all high."""
    flag = high.shift(1).fillna(False).astype(int)
    return (flag.rolling(days, min_periods=days).sum() == days).fillna(False)


def episode_starts(label: pd.Series) -> pd.Series:
    """First day of each run of true labels. Unknown days are never starts."""
    true = label.fillna(False).astype(bool)
    return (true & ~true.shift(1, fill_value=False)).rename(label.name)


def eligible(starts: pd.Series, horizon: int = HORIZON) -> pd.Series:
    """A day can fire only if no episode has already started inside the horizon.

    The prior horizon bars are the ones that would still claim this episode,
    so counting this day as well would count the same episode twice.
    """
    prior = starts.astype(int).rolling(horizon, min_periods=1).sum().shift(1).fillna(0)
    return prior.eq(0)


def preceded_by(fires: pd.Series, label: pd.Series, horizon: int) -> pd.Series:
    """1 when a fire landed in the horizon before this bar, else 0.

    The value is only defined on an episode start. Every other bar is NaN,
    so the base rate is the share of starts that were preceded by a fire
    and the denominator is the episode count.
    """
    flag = fires.fillna(False).astype(int)
    prior = flag.rolling(horizon, min_periods=1).sum().shift(1).fillna(0)
    starts = episode_starts(label)
    out = pd.Series(np.nan, index=label.index)
    out[starts] = (prior[starts] > 0).astype(float)
    return out.rename("preceded")


def followed_by(label: pd.Series, horizon: int = HORIZON) -> pd.Series:
    """True when a new episode starts on one of the next h days.

    Scoring against any labelled day makes the base rate the share of days
    inside a run, which is most days once a drawdown is underway. The event
    being detected is the start. The last h bars are unknown and stay NaN.
    """
    starts = episode_starts(label)
    values = starts.fillna(False).to_numpy(dtype=bool)
    n = len(values)
    out = np.full(n, np.nan)
    for i in range(n - horizon):
        out[i] = float(values[i + 1:i + 1 + horizon].any())
    return pd.Series(out, index=label.index, name="followed")


def false_alarm_return(close: pd.Series, fires: pd.Series, followed: pd.Series,
                       horizon: int = HORIZON) -> float:
    """Mean close-to-close return over the horizon on fires that missed.

    The return uses the close at t and the close h days later, both known
    once the window has closed. Fires whose window is open are excluded.
    """
    price = close.to_numpy(dtype=float)
    n = len(price)
    forward = np.full(n, np.nan)
    if n > horizon:
        forward[: n - horizon] = price[horizon:] / price[: n - horizon] - 1
    mask = fires.fillna(False).to_numpy(dtype=bool) & (followed.to_numpy(dtype=float) == 0)
    taken = forward[mask]
    taken = taken[~np.isnan(taken)]
    return float(taken.mean()) if len(taken) else float("nan")


def lead_times(fires: pd.Series, label: pd.Series, horizon: int = HORIZON) -> list[int]:
    """Days from the first fire of a quiet spell to the episode start it preceded.

    One number per episode. A fire that does not precede a start is absent.
    """
    fire_at = fires.fillna(False).to_numpy(dtype=bool)
    start_at = episode_starts(label).fillna(False).to_numpy(dtype=bool)
    index = fires.index
    leads = []
    quiet = True
    first = None
    claimed = np.zeros(len(fire_at), dtype=bool)
    for i, flag in enumerate(fire_at):
        if not flag:
            quiet = True
            continue
        if quiet:
            first = i
            quiet = False
        window = start_at[i + 1:i + 1 + horizon]
        if not window.any():
            continue
        hit = i + 1 + int(np.argmax(window))
        if claimed[hit]:
            continue
        claimed[hit] = True
        leads.append(int((index[hit] - index[first]).days))
        first = None
        quiet = True
    return leads


def _block(fires: pd.Series, followed: pd.Series, eligible_days: pd.Series) -> dict:
    decided = followed.notna() & eligible_days.fillna(False)
    base_n = int(decided.sum())
    base_hits = int((followed.eq(1) & decided).sum())
    fired = fires.fillna(False) & decided
    n = int(fired.sum())
    hits = int((fired & followed.eq(1)).sum())
    rate = hits / n if n else float("nan")
    base = base_hits / base_n if base_n else float("nan")
    lift = rate / base if base else float("nan")
    return {
        "fires": n,
        "hits": hits,
        "rate": rate,
        "base_fires": base_n,
        "base_hits": base_hits,
        "base_rate": base,
        "lift": lift,
    }


def score_factor(fires: pd.Series, followed: pd.Series, eligible_days: pd.Series,
                 period: pd.Series) -> dict:
    """Lift against the base rate, for the whole sample, each period and each year."""
    frame = pd.DataFrame({
        "fires": fires.fillna(False).astype(bool),
        "followed": followed,
        "eligible": eligible_days.fillna(False).astype(bool),
        "period": period,
        "year": fires.index.year,
    })

    def take(group: pd.DataFrame) -> dict:
        return _block(group["fires"], group["followed"], group["eligible"])

    by_period = {name: take(group) for name, group in frame.groupby("period") if pd.notna(name)}
    by_year = {int(year): take(group) for year, group in frame.groupby("year")}
    return {"all": take(frame), "by_period": by_period, "by_year": by_year}


def bootstrap_lift(fires: pd.Series, followed: pd.Series, eligible_days: pd.Series,
                   draws: int = BOOTSTRAP_DRAWS, seed: int = BOOTSTRAP_SEED) -> dict:
    """90 percent interval for the lift, resampling eligible days with replacement.

    Each draw recomputes both the hit rate and the base rate, so the interval
    is on the lift and not on the hit rate alone. Fewer than two fires returns
    an empty interval rather than a number built from nothing.
    """
    decided = (followed.notna() & eligible_days.fillna(False)).to_numpy()
    hit = followed.eq(1).to_numpy()
    fired = fires.fillna(False).to_numpy(dtype=bool)
    n = int(decided.sum())
    if n < 2 or int(fired.sum()) < 2:
        return {"lo": float("nan"), "hi": float("nan"), "draws": 0, "n": n}
    rng = np.random.default_rng(seed)
    lifts = np.empty(draws)
    for draw in range(draws):
        chosen = rng.integers(0, n, n)
        base = hit[chosen].mean()
        taken = fired[chosen]
        rate = hit[chosen][taken].mean() if taken.any() else np.nan
        lifts[draw] = rate / base if base else np.nan
    finite = lifts[~np.isnan(lifts)]
    if len(finite) < draws // 2:
        return {"lo": float("nan"), "hi": float("nan"), "draws": int(len(finite)), "n": n}
    lo, hi = np.quantile(finite, [0.05, 0.95])
    return {"lo": float(lo), "hi": float(hi), "draws": int(len(finite)), "n": n}
