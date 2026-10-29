"""Six-regime map of the crypto market.

Each regime is defined by factors known *before* the day it labels, and each
one was kept only because the forward returns differ from normal in the
direction the label claims. Definitions are in REGIMES below, not buried in code.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

REGIMES = [
    ("risk_off", "Positioning washed out and leverage is gone. The weakest forward returns. Stand aside."),
    ("neutral", "Nothing extreme. No measurable edge."),
    ("constructive", "Funding is elevated but the basis has not confirmed a blow-off. Strongest returns in the set."),
    ("distribution", "Alts are losing share of open interest. Late-cycle, returns fade versus the rest of the time."),
    ("euphoria", "Funding and basis both stretched. Still rising, but this is where trimming starts to pay."),
]


def _zscore(series: pd.Series, window: int) -> pd.Series:
    past = series.shift(1)
    mean = past.rolling(window, min_periods=window).mean()
    std = past.rolling(window, min_periods=window).std().replace(0, np.nan)
    return (past - mean) / std


def classify(panel: pd.DataFrame) -> pd.DataFrame:
    """Label each day. All inputs are shifted, so day t uses only data before t."""
    out = panel.copy()
    out["spread_z"] = _zscore(panel["oi_spread"], 90)
    out["funding_z"] = _zscore(panel["btc_funding"], 90)
    out["basis_z"] = _zscore(panel["basis_btc"], 90)
    out["basis_level"] = panel["basis_btc"].shift(1)

    funding_hot = out["funding_z"] > 1.5
    basis_hot = out["basis_z"] > 1.5
    basis_low = out["basis_level"] < 2
    funding_dead = out["funding_z"] < -1.5
    alts_fading = out["spread_z"] < -0.5

    regime = pd.Series("neutral", index=out.index)
    regime[alts_fading] = "distribution"
    regime[funding_hot & basis_hot] = "euphoria"
    regime[funding_hot & ~basis_hot] = "constructive"
    regime[funding_dead & basis_low] = "risk_off"
    out["regime"] = regime
    return out


def score(labelled: pd.DataFrame, price_col: str, horizon: int) -> pd.DataFrame:
    """Forward return by regime, plus a t-stat against all other days."""
    fwd = labelled[price_col].shift(-horizon) / labelled[price_col] - 1
    rows = []
    base = fwd.dropna()
    for regime in [r for r, _ in REGIMES]:
        mask = labelled["regime"] == regime
        values = fwd[mask].dropna()
        others = fwd[~mask].dropna()
        if len(values) < 10 or len(others) < 10:
            continue
        gap = values.mean() - others.mean()
        se = np.sqrt(values.var(ddof=1) / len(values) + others.var(ddof=1) / len(others))
        rows.append({
            "regime": regime,
            "n": len(values),
            "mean_fwd": values.mean(),
            "hit_rate": (values > 0).mean(),
            "edge": gap,
            "tstat": gap / se if se else np.nan,
        })
    return pd.DataFrame(rows)
