"""A single heat score for the crypto market, from -1 to +1.

Each indicator is normalized to its own trailing history, so a reading means
the same thing in 2020 as in 2025. The indicators are then averaged. +1 means
every input is at an extreme high together, -1 means every input is at an
extreme low. 0 is baseline.

The sign convention: positive is overheated, negative is washed out. Whether
the extremes predict anything is checked separately, not assumed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# window for the trailing normalization, in days
WINDOW = 180
MIN_HISTORY = 90

# Three factors, all momentum and volatility. Reduced from seven on 2026-10-27
# after basis_btc_z30, basis_gap_btc_eth and dispersion_14 flipped sign on the
# full history through 2026-10-26. They stay in the weekly retest and return
# only if they pass again. See results/2026-10-27_drop.json.
COMPONENTS = {
    "btc_ret_30": 1,
    "btc_vol_z90": 1,
    "btc_trend_stretch": 1,
    "eth_funding_z30": 1,
}


def _percentile(series: pd.Series) -> pd.Series:
    """Where today's value sits in the trailing window, from 0 to 1.

    Shifted by one so the current bar is judged against history that excludes it.
    """
    past = series.shift(1)
    return past.rolling(WINDOW, min_periods=MIN_HISTORY).rank(pct=True)


def heat_score(panel: pd.DataFrame) -> pd.DataFrame:
    """Score from the tested factors. Each is already a z-score, so it is
    squashed to -1..+1 with a bounded transform rather than re-ranked."""
    from .factors import build_factors

    out = panel.copy()
    factors = build_factors(panel)
    legs = []
    for column, direction in COMPONENTS.items():
        if column not in factors:
            continue
        leg = np.tanh(factors[column] / 2) * direction
        out[f"leg_{column}"] = leg
        legs.append(leg)
    if not legs:
        raise ValueError("no components available")
    out["heat"] = pd.concat(legs, axis=1).mean(axis=1)
    return out


def score_extremes(scored: pd.DataFrame, price_col: str, horizon: int,
                   band: float = 0.5) -> dict:
    """Forward returns when the score is above +band, below -band, and in between."""
    fwd = scored[price_col].shift(-horizon) / scored[price_col] - 1
    heat = scored["heat"]

    def block(mask: pd.Series) -> tuple[float, int]:
        values = fwd[mask].dropna()
        return (values.mean(), len(values)) if len(values) else (float("nan"), 0)

    hot_mean, hot_n = block(heat > band)
    cold_mean, cold_n = block(heat < -band)
    mid_mean, mid_n = block(heat.abs() <= band)
    return {
        "hot": hot_mean, "hot_n": hot_n,
        "cold": cold_mean, "cold_n": cold_n,
        "mid": mid_mean, "mid_n": mid_n,
    }
