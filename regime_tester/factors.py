"""Candidate factors for the heat score, and a test for which ones predict.

A factor earns a place only if its extreme predicts the forward return in the
first half of the sample AND in the second half, with the same sign. Anything
that flips is dropped, however good it looks overall.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

FORWARD_DAYS = 10


def build_factors(panel: pd.DataFrame) -> pd.DataFrame:
    """One column per candidate. All use only data available that day."""
    f = pd.DataFrame(index=panel.index)
    btc = panel["btc_price"]
    eth = panel["eth_price"]
    alt = panel["alt_price"]

    def zscore(series: pd.Series, window: int) -> pd.Series:
        past = series.shift(1)
        mean = past.rolling(window, min_periods=window // 2).mean()
        std = past.rolling(window, min_periods=window // 2).std().replace(0, np.nan)
        return (past - mean) / std

    def rank(series: pd.Series, window: int) -> pd.Series:
        return series.shift(1).rolling(window, min_periods=window // 2).rank(pct=True)

    # positioning levels
    for col in ("btc_funding", "eth_funding", "alt_funding", "basis_btc", "basis_eth", "oi_spread"):
        if col in panel:
            f[f"{col}_z90"] = zscore(panel[col], 90)
            f[f"{col}_z30"] = zscore(panel[col], 30)

    # spreads between assets: where is leverage concentrated
    f["funding_gap_btc_eth"] = zscore(panel["btc_funding"] - panel["eth_funding"], 90)
    f["basis_gap_btc_eth"] = zscore(panel["basis_btc"] - panel["basis_eth"], 90)

    # trend and momentum
    for window in (7, 30, 90):
        f[f"btc_ret_{window}"] = zscore(btc.pct_change(window), 180)
        f[f"eth_ret_{window}"] = zscore(eth.pct_change(window), 180)

    # eth relative strength versus btc
    ratio = eth / btc
    f["eth_btc_ratio_z90"] = zscore(ratio, 90)

    # realized volatility regime
    realized = btc.pct_change().rolling(14).std()
    f["btc_vol_z90"] = zscore(realized, 90)
    f["btc_vol_change"] = zscore(realized.pct_change(7), 90)

    # drawdown from trailing high: how deep the pullback is
    high = btc.rolling(90, min_periods=30).max()
    f["btc_drawdown"] = (btc / high - 1).shift(1)

    # trend stretch: distance from the 50 day average
    f["btc_trend_stretch"] = zscore(btc / btc.rolling(50).mean() - 1, 180)

    # acceleration: is momentum speeding up or fading
    momentum = btc.pct_change(14)
    f["btc_acceleration"] = zscore(momentum - momentum.shift(14), 120)

    # cross-asset breadth proxy: alt basket versus btc
    f["alt_vs_btc"] = zscore((alt.pct_change(14) - btc.pct_change(14)), 120)

    if "dispersion_14" in panel:
        f["dispersion_14"] = zscore(panel["dispersion_14"], 90)

    return f


def test_factors(factors: pd.DataFrame, price: pd.Series) -> pd.DataFrame:
    """Keep factors whose extreme predicts returns with the same sign in both halves."""
    fwd = price.shift(-FORWARD_DAYS) / price - 1
    mid = factors.index[len(factors) // 2]
    rows = []
    for column in factors.columns:
        leg = factors[column]
        both = pd.concat([leg.rename("x"), fwd.rename("f")], axis=1).dropna()
        if len(both) < 200:
            continue
        for half, sl in (("train", both.index <= mid), ("test", both.index > mid)):
            part = both[sl]
            top = part[part["x"] > part["x"].quantile(0.8)]["f"]
            bot = part[part["x"] < part["x"].quantile(0.2)]["f"]
            if len(top) < 15 or len(bot) < 15:
                continue
            gap = top.mean() - bot.mean()
            se = np.sqrt(top.var(ddof=1) / len(top) + bot.var(ddof=1) / len(bot))
            rows.append({"factor": column, "half": half, "gap": gap,
                         "tstat": gap / se if se else np.nan, "n": len(top)})
    if not rows:
        return pd.DataFrame()
    table = pd.DataFrame(rows)
    wide = table.pivot(index="factor", columns="half", values="gap")
    # same sign in both halves, and the test half is not negligible
    keep = wide[(wide["train"] * wide["test"] > 0) & (wide["test"].abs() > 0.005)]
    return keep.sort_values("test", key=lambda s: s.abs(), ascending=False)
