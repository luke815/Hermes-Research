"""Shared scoring for the C3 to C7 cycle families.

The rules are fixed in research/log.md under the 2026-11-10 pre-registration.
This module computes them. It does not choose a threshold, a horizon or a
label, and it does not decide a verdict.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from regime_tester.costs import apply_costs
from regime_tester.episodes import bottom_event, episodes, top_event
from regime_tester.events import (
    bootstrap_lift,
    episode_starts,
    false_alarm_return,
    followed_by,
    lead_times,
    preceded_by,
    rolling_percentile,
    score_factor,
)
from regime_tester.periods import assign_period

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

HORIZON = 30
NEAR = 0.05
LOOKBACK = 60
PRIMARY = {"top": 0.90, "bottom": 0.10}
NEIGHBOURS = {"top": (0.85, 0.95), "bottom": (0.05, 0.15)}
LABELS = (
    {"name": "top_30_20", "side": "top", "kind": "top", "h": 30, "x": 0.20, "y": None, "primary": True},
    {"name": "top_20_15", "side": "top", "kind": "top", "h": 20, "x": 0.15, "y": None, "primary": False},
    {"name": "top_60_30", "side": "top", "kind": "top", "h": 60, "x": 0.30, "y": None, "primary": False},
    {"name": "bottom_30_20_7", "side": "bottom", "kind": "bottom", "h": 30, "x": 0.20, "y": 0.07, "primary": True},
    {"name": "bottom_60_30_10", "side": "bottom", "kind": "bottom", "h": 60, "x": 0.30, "y": 0.10, "primary": False},
)
MIN_EPISODES = 30
BOOTSTRAP_DRAWS = 2000


def load_ohlcv() -> dict[str, pd.DataFrame]:
    """Daily bars per asset from the retained Coinalyze file. No pull."""
    blob = json.loads((RAW / "coinalyze_ohlcv-history.json").read_text())
    names = {symbol: asset for asset, symbol in blob["symbols"].items()}
    out = {}
    for entry in blob["data"]:
        frame = pd.DataFrame(entry["history"])
        index = pd.to_datetime(frame["t"], unit="s", utc=True).dt.normalize()
        taken = frame.loc[:, ["o", "h", "l", "c", "v"]].apply(pd.to_numeric, errors="coerce")
        taken.index = index
        taken = taken[~taken.index.duplicated(keep="last")].sort_index()
        out[names[entry["symbol"]]] = taken
    return out


def load_pooled() -> dict[str, pd.DataFrame]:
    """Daily bars from the point-in-time panel, every name with 60 closes.

    Close and volume only. Open and high are the close, because the panel does
    not store them, and a script that needs the true range cannot use this.
    """
    out = {}
    panel = ROOT / "data" / "panel_xs"
    for name in sorted(os.listdir(panel)):
        frame = pd.read_csv(panel / name)
        if "close" not in frame.columns or frame["close"].notna().sum() < 60:
            continue
        frame = frame.dropna(subset=["close"])
        frame["date"] = pd.to_datetime(frame["date"], utc=True)
        taken = pd.DataFrame({
            "o": frame["close"], "h": frame["close"], "l": frame["close"],
            "c": frame["close"], "v": frame.get("volume_base", 0),
        })
        taken.index = frame["date"]
        out[name.replace(".csv", "")] = taken[~taken.index.duplicated(keep="last")].sort_index()
    return out


def load_funding() -> dict[str, pd.Series]:
    blob = json.loads((RAW / "coinalyze_funding-rate-history.json").read_text())
    names = {symbol: asset for asset, symbol in blob["symbols"].items()}
    out = {}
    for entry in blob["data"]:
        frame = pd.DataFrame(entry["history"])
        index = pd.to_datetime(frame["t"], unit="s", utc=True).dt.normalize()
        series = pd.to_numeric(frame["c"], errors="coerce")
        series.index = index
        series = series[~series.index.duplicated(keep="last")].sort_index()
        if entry["symbol"] not in names:
            continue
        out[names[entry["symbol"]]] = series
    return out


def load_tenor(kind: str, token: str, tenor: str = "30") -> pd.Series:
    """One options series, joined across the window files already on disk."""
    rows = []
    for path in sorted(RAW.glob(f"{kind}_{token.lower()}*.json")):
        loaded = json.loads(path.read_text())
        if isinstance(loaded, list):
            rows.extend(loaded)
    by_date: dict[pd.Timestamp, float] = {}
    for row in rows:
        if "date" not in row or tenor not in row:
            continue
        value = row[tenor]
        if not isinstance(value, (int, float)):
            continue
        stamp = pd.to_datetime(row["date"], unit="ms", utc=True).normalize()
        by_date[stamp] = float(value)
    return pd.Series(by_date, dtype=float).sort_index().rename(f"{kind}_{token.lower()}_{tenor}")


def load_fear_greed() -> pd.Series:
    rows = json.loads((RAW / "fear_greed.json").read_text())
    by_date = {}
    for row in rows:
        stamp = pd.to_datetime(int(row["timestamp"]), unit="s", utc=True).normalize()
        by_date[stamp] = float(row["value"])
    return pd.Series(by_date, dtype=float).sort_index().rename("fear_greed")


def candidate_mask(close: pd.Series, side: str) -> pd.Series:
    """Within 5 percent of the trailing 60-day extreme, extreme from past bars only."""
    past = close.shift(1)
    if side == "top":
        extreme = past.rolling(LOOKBACK, min_periods=LOOKBACK).max()
        near = close >= extreme * (1 - NEAR)
    else:
        extreme = past.rolling(LOOKBACK, min_periods=LOOKBACK).min()
        near = close <= extreme * (1 + NEAR)
    return near.fillna(False)


def event_label(close: pd.Series, spec: dict) -> pd.Series:
    if spec["kind"] == "top":
        label = top_event(close, spec["h"], spec["x"])
    else:
        label = bottom_event(close, spec["h"], spec["x"], spec["y"])
    return label.where(candidate_mask(close, spec["side"]))


def year_caveat(label: pd.Series) -> dict:
    """Flag a label whose episodes pile into one calendar year."""
    ids = episodes(label)
    true = ids[ids > 0]
    if true.empty:
        return {"episodes": 0, "worst_year": None, "worst_share": None, "caveat": False}
    per_year = true.groupby(true.index.year).nunique()
    worst = int(per_year.max())
    total = int(true.nunique())
    return {
        "episodes": total,
        "worst_year": int(per_year.idxmax()),
        "worst_share": worst / total if total else None,
        "caveat": bool(total and worst / total > 0.5),
    }


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (np.floating, float)):
        if np.isnan(value) or np.isinf(value):
            return None
        return round(float(value), 6)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    return value


def evaluate(name: str, side: str, rank: pd.Series, cut: float, label: pd.Series,
             close: pd.Series, funding: pd.Series | None, horizon: int,
             seed: int) -> dict:
    """One factor, one cut, one asset.

    A fire is an extreme reading on a candidate day. An episode counts as
    caught when a fire landed in the horizon before its start, so the hit
    rate and the base rate are both shares of episode starts and the
    denominator is the episode count. A fire that precedes no start is a
    false alarm, and its return is reported separately.
    """
    candidates = candidate_mask(close, side).reindex(rank.index).fillna(False)
    extreme = rank.ge(cut) if side == "top" else rank.le(cut)
    fires = extreme & rank.notna() & candidates
    starts = episode_starts(label)
    caught = preceded_by(fires, label, horizon)
    period = assign_period(rank.index)
    scored = score_factor(fires, caught, starts, period)
    intervals = {}
    for period_name in ("train", "validation", "test"):
        mask = period.eq(period_name).reindex(rank.index).fillna(False)
        intervals[period_name] = bootstrap_lift(
            fires[mask], caught[mask], starts[mask], draws=BOOTSTRAP_DRAWS, seed=seed)
    leads = lead_times(fires, label, horizon)
    gross = apply_costs(close, horizon, side=1 if side == "bottom" else -1,
                        funding=funding, oi_usd=None)
    followed = followed_by(label, horizon)
    miss = fires.fillna(False) & followed.eq(0)
    decided = followed.notna() & fires.fillna(False)
    false_share = None if not decided.any() else float((followed.eq(0) & decided).sum() / decided.sum())
    return {
        "name": name,
        "side": side,
        "cut": cut,
        "score": scored,
        "bootstrap": intervals,
        "lead_days_median": float(np.median(leads)) if leads else None,
        "lead_days_n": len(leads),
        "false_alarm_share": false_share,
        "false_alarm_return_gross": false_alarm_return(close, fires, followed, horizon),
        "false_alarm_return_net": float(gross.loc[miss, "net"].mean()) if miss.any() else None,
        "episodes_total": int(episodes(label).max()) if len(label) else 0,
        "denominator": "episode starts preceded by a fire within the horizon",
    }


def holds(primary: dict, neighbours: list[dict]) -> bool:
    """The lift stays on the same side of 1 at both neighbour cuts, in validation."""
    base = primary["score"]["by_period"].get("validation", {}).get("lift")
    if base is None or (isinstance(base, float) and np.isnan(base)):
        return False
    for other in neighbours:
        lift = other["score"]["by_period"].get("validation", {}).get("lift")
        if lift is None or (isinstance(lift, float) and np.isnan(lift)):
            return False
        if (base - 1) * (lift - 1) <= 0:
            return False
    return True


def train_val_episodes(row: dict) -> int:
    total = 0
    for period_name in ("train", "validation"):
        block = row["score"]["by_period"].get(period_name, {})
        total += int(block.get("fires") or 0)
    return total


def verdict_for(row: dict, neighbours_hold: bool) -> str:
    """Apply the amended bar. Returns the one-line verdict, nothing more."""
    train = row["score"]["by_period"].get("train", {})
    validation = row["score"]["by_period"].get("validation", {})
    test = row["score"]["by_period"].get("test", {})
    n = train_val_episodes(row)
    if n < MIN_EPISODES:
        return "insufficient"
    train_lift = train.get("lift")
    val_lift = validation.get("lift")
    if train_lift is None or val_lift is None:
        return "insufficient"
    if (train_lift - 1) * (val_lift - 1) <= 0 or val_lift <= 1:
        return "rejected"
    interval = row["bootstrap"].get("validation", {})
    lo = interval.get("lo")
    if lo is None or (isinstance(lo, float) and np.isnan(lo)) or lo <= 1:
        return "rejected"
    if not neighbours_hold:
        return "rejected"
    test_episodes = int(test.get("base_hits") or 0)
    if test_episodes >= 10:
        test_lift = test.get("lift")
        if test_lift is None or (test_lift - 1) * (val_lift - 1) <= 0:
            return "rejected"
        return "admitted"
    return "admitted, test pending"
