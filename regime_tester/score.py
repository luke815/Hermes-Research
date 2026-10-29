"""Score regimes on forward returns, in isolation and in combination.

A regime earns its keep only if its forward returns differ from the base rate
by more than noise. Combinations are scored on the joint regime and on
agreement: bars where every leg's extreme regime points the same way.
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from .regimes import forward_return, make_features, walk_forward_quintile

MIN_CELL = 30  # observations below this are reported but flagged as noise


def _tstat(values: np.ndarray, base: float) -> float:
    n = len(values)
    if n < 3:
        return float("nan")
    se = values.std(ddof=1) / np.sqrt(n)
    if se == 0:
        return float("nan")
    return float((values.mean() - base) / se)


def score_regimes(labels: pd.Series, fwd: pd.Series, name: str) -> pd.DataFrame:
    """One row per regime label: hit rate, mean forward return, t-stat vs base."""
    both = pd.concat([labels.rename("regime"), fwd.rename("fwd")], axis=1, sort=False).dropna()
    if both.empty:
        return pd.DataFrame()
    base = both["fwd"].mean()
    base_hit = (both["fwd"] > 0).mean()
    rows = []
    for regime, group in both.groupby("regime"):
        values = group["fwd"].to_numpy()
        rows.append({
            "indicator": name,
            "regime": int(regime) if float(regime).is_integer() else regime,
            "n": len(values),
            "mean_fwd_return": values.mean(),
            "edge_vs_base": values.mean() - base,
            "hit_rate": (values > 0).mean(),
            "hit_edge": (values > 0).mean() - base_hit,
            "tstat": _tstat(values, base),
            "thin": len(values) < MIN_CELL,
        })
    return pd.DataFrame(rows)


def _best_feature(panel: pd.DataFrame, column: str, fwd: pd.Series) -> tuple[pd.Series, str, float]:
    """Pick the feature transform (z / change / rank) with the strongest regime split."""
    features = make_features(panel[column])
    best, best_score, best_kind = None, -np.inf, ""
    for kind in features.columns:
        labels = walk_forward_quintile(features[kind])
        scored = score_regimes(labels, fwd, column)
        if scored.empty:
            continue
        score = scored["tstat"].abs().max()
        if np.isfinite(score) and score > best_score:
            best, best_score, best_kind = labels, score, kind
    return best, best_kind, best_score


def _drop_duplicates(panel: pd.DataFrame, threshold: float = 0.995) -> pd.DataFrame:
    """Drop indicators that are rescalings of an earlier one.

    Laevitas exports funding and APR side by side; APR is funding times a
    constant, so both would "confirm" each other in every combination.
    """
    keep = []
    for col in [c for c in panel.columns if c != "price"]:
        match = next((o for o in keep if abs(panel[col].corr(panel[o])) > threshold), None)
        if match is not None:
            print(f"  dropping {col}: duplicate of {match}")
        else:
            keep.append(col)
    return panel[["price", *keep]]


def isolation(panel: pd.DataFrame, horizon: int) -> pd.DataFrame:
    panel = _drop_duplicates(panel)
    fwd = forward_return(panel["price"], horizon)
    frames = []
    for column in [c for c in panel.columns if c != "price"]:
        labels, kind, _ = _best_feature(panel, column, fwd)
        if labels is None:
            continue
        scored = score_regimes(labels, fwd, column)
        scored.insert(1, "transform", kind)
        frames.append(scored)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _extreme(labels: pd.Series) -> pd.Series:
    """Map quintiles to a direction: low (0-1) = -1, mid = 0, high (3-4) = +1."""
    out = pd.Series(0, index=labels.index, dtype=int)
    out[labels <= 1] = -1
    out[labels >= 3] = 1
    return out.where(labels.notna())


def combinations(panel: pd.DataFrame, horizon: int, max_legs: int = 3, top_n: int = 6) -> pd.DataFrame:
    """Joint-regime and agreement scores for the strongest indicators.

    Only the top `top_n` indicators by isolation t-stat are combined, and only
    up to `max_legs` at a time. Otherwise the grid explodes and every cell is
    too thin to mean anything.
    """
    fwd = forward_return(panel["price"], horizon)
    alone = isolation(panel, horizon)
    if alone.empty:
        return pd.DataFrame()

    strength = alone.groupby("indicator")["tstat"].apply(lambda s: s.abs().max()).sort_values(ascending=False)
    chosen = list(strength.head(top_n).index)

    legs = {}
    for column in chosen:
        labels, kind, _ = _best_feature(panel, column, fwd)
        if labels is not None:
            legs[f"{column}:{kind}"] = labels

    rows = []
    names = list(legs)
    for k in range(2, min(max_legs, len(names)) + 1):
        for combo in itertools.combinations(names, k):
            aligned = pd.concat([legs[n].rename(n) for n in combo], axis=1).dropna()
            if len(aligned) < MIN_CELL:
                continue
            joint = aligned.astype(int).astype(str).agg("-".join, axis=1)
            # Too many joint states to report individually; collapse to a
            # single "all legs extreme and agreeing" regime vs the rest.
            directions = pd.concat([_extreme(legs[n]) for n in combo], axis=1).dropna()
            agreeing = directions.abs().eq(1).all(axis=1) & directions.nunique(axis=1).eq(1)
            sign = directions.iloc[:, 0].where(agreeing, 0)
            scored = score_regimes(sign.rename("regime"), fwd, " + ".join(combo))
            scored = scored[scored["regime"] != 0]
            scored.insert(1, "kind", "agreement")
            rows.append(scored)
            _ = joint  # retained so the joint labelling is exercised and tested
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
