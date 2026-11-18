"""Costs table and net-return plumbing.

Every backtest return is reported net of three things: a taker fee on both
sides, a slippage assumption that depends on the open interest known at
entry, and the funding carry paid while the position is held.

The Coinalyze funding close is a percent per 8-hour settlement (median near
0.01, which is the Binance base rate of 0.01 percent). One settlement per
day is accrued, so the daily carry in return units is the close divided by
100. A long pays positive funding; a short receives it.

Nothing here looks past the bar it is scoring. The price return from day t
uses the close at t and the close h days later, both known once the window
has closed, and the carry sums the funding closes inside that same window.
Open interest is shifted one bar, so the tier at entry uses the last
completed bar.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Rates are in return units: 0.0005 is 5 basis points.
TAKER_FEE_PER_SIDE = 0.0005
SLIPPAGE_LIQUID_PER_SIDE = 0.0010
SLIPPAGE_THIN_PER_SIDE = 0.0025
LIQUID_OI_USD = 50_000_000
SIDES = 2

# Coinalyze funding close is a percent per 8-hour settlement. Accrued once
# per day, the daily carry in return units is the close divided by this.
FUNDING_PERCENT_PER_SETTLEMENT = 100.0


def costs_table() -> pd.DataFrame:
    """The rates, one row per venue tier. This is the table later tests read."""
    return pd.DataFrame([
        {"tier": "liquid", "oi_min_usd": LIQUID_OI_USD, "taker_fee_per_side": TAKER_FEE_PER_SIDE,
         "slippage_per_side": SLIPPAGE_LIQUID_PER_SIDE},
        {"tier": "thin", "oi_min_usd": 0, "taker_fee_per_side": TAKER_FEE_PER_SIDE,
         "slippage_per_side": SLIPPAGE_THIN_PER_SIDE},
    ])


def round_trip(oi_usd: float | None) -> float:
    """Fee plus slippage, both sides. Missing open interest takes the thin tier,
    which is the more expensive assumption and is flagged by the caller."""
    slip = SLIPPAGE_LIQUID_PER_SIDE if (oi_usd is not None and oi_usd >= LIQUID_OI_USD) else SLIPPAGE_THIN_PER_SIDE
    return SIDES * (TAKER_FEE_PER_SIDE + slip)


def _window_sum(values: np.ndarray, horizon: int) -> np.ndarray:
    """Sum of values[i : i + horizon] at each i. The last horizon rows are NaN,
    because that window has not closed yet."""
    out = np.full(len(values), np.nan)
    if horizon < 1:
        raise ValueError("horizon must be at least 1")
    csum = np.cumsum(np.where(np.isnan(values), 0.0, values))
    valid = np.cumsum(np.isnan(values).astype(int))
    for i in range(len(values) - horizon + 1):
        missing = valid[i + horizon - 1] - (valid[i - 1] if i else 0)
        if missing:
            continue
        total = csum[i + horizon - 1] - (csum[i - 1] if i else 0)
        out[i] = total
    return out


def apply_costs(price: pd.Series, horizon: int, side: int,
                funding: pd.Series | None = None,
                oi_usd: pd.Series | None = None) -> pd.DataFrame:
    """Gross and net forward return at one horizon.

    side is +1 for a long and -1 for a short. The gross return is the price
    change over the window signed by the position. The net return subtracts
    the round trip and the funding carry. Carry is NaN wherever funding is
    missing, and the net return is NaN with it: a missing carry is never
    treated as zero.

    Open interest is shifted one bar before the tier is chosen, so the tier
    at day t uses the bar that had already closed.
    """
    if side not in (1, -1):
        raise ValueError("side must be +1 or -1")
    px = price.astype(float)
    gross = side * (px.shift(-horizon) / px - 1)

    if oi_usd is None:
        known = pd.Series(np.nan, index=px.index)
        oi_missing = True
    else:
        known = oi_usd.shift(1).reindex(px.index)
        oi_missing = False
    cost = known.map(lambda v: round_trip(None if pd.isna(v) else float(v)))

    if funding is None:
        carry = pd.Series(np.nan, index=px.index)
        funding_missing = True
    else:
        daily = funding.reindex(px.index).astype(float) / FUNDING_PERCENT_PER_SETTLEMENT
        # window t .. t+horizon-1: the settlements inside the holding period
        carry = pd.Series(_window_sum(daily.to_numpy(), horizon), index=px.index) * side
        funding_missing = False

    return pd.DataFrame({
        "gross": gross,
        "round_trip": cost,
        "carry": carry,
        "net": gross - cost - carry,
        "oi_missing": oi_missing,
        "funding_missing": funding_missing,
    })
