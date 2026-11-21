"""Exposure strategies: an exposure series times next-day returns.

An exposure of 1 is buy and hold apart from the cost of opening it. A
change in exposure is charged the costs table on the size of the change,
and the funding carry is charged on the exposure held. The benchmarks are
buy and hold and the 200-day rule, scored on the same dates. Nothing here
looks past the bar it is scoring: the return at t uses the close at t and
the close at t+1, and the carry uses the funding close at t.
"""

from __future__ import annotations

import pandas as pd

from regime_tester.costs import FUNDING_PERCENT_PER_SETTLEMENT, round_trip


def exposure_returns(close, exposure, funding=None, oi_usd=None):
    """Next-day return of an exposure series, net of costs and carry.

    `exposure` is the fraction of gross held from each close to the next.
    The cost is charged on the absolute change in exposure, including the
    opening change from flat. A missing funding value leaves that day's
    carry missing rather than treating it as zero.
    """
    price = close.astype(float)
    held = exposure.astype(float).reindex(price.index)
    forward = price.shift(-1) / price - 1
    gross = held * forward
    change = held.diff()
    change.iloc[0] = held.iloc[0]
    cost = change.abs() * round_trip(oi_usd)
    if funding is None:
        carry = pd.Series(0.0, index=price.index)
    else:
        carry = held * funding.astype(float).reindex(price.index) / FUNDING_PERCENT_PER_SETTLEMENT
    net = gross - cost - carry
    return pd.DataFrame({"gross": gross, "cost": cost, "carry": carry, "net": net})


def buy_and_hold(close, funding=None, oi_usd=None):
    """Exposure of 1 every day, so the only cost is the opening trade."""
    return exposure_returns(close, pd.Series(1.0, index=close.index), funding, oi_usd)


def rule_200d(close, funding=None, oi_usd=None):
    """Long when the close is at or above its own trailing 200-day average.

    The average at t uses closes through t, which is known at the close the
    exposure is set. The first 199 bars have no average and stay flat.
    """
    average = close.astype(float).rolling(200, min_periods=200).mean()
    exposure = (close.astype(float) >= average).astype(float)
    exposure = exposure.where(average.notna(), 0.0)
    return exposure_returns(close, exposure, funding, oi_usd)
