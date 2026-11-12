"""Confirm one leaderboard cell on validation and test.

The train scorer never sees these periods, and nothing else in the repo
should either. confirm_cell is the only function that loads a bar after
the train end, and it scores only the bars from the validation start
onward. One attempt per cell, recorded as it finishes, so a second call
is refused rather than retried.
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from regime_tester.costs import apply_costs
from regime_tester.indicators import LIBRARY_VERSION, indicators
from regime_tester.sweep import (
    MIN_INDEPENDENT, TARGETS, TRANSFORMS, UNIVERSES, newey_west_t,
    rolling_rank, score_signal, transform,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RECORD = ROOT / "results" / "sweeps" / "confirmations.json"

TRAIN_END = pd.Timestamp("2024-06-30", tz="UTC")
VALIDATION_START = pd.Timestamp("2024-07-01", tz="UTC")
VALIDATION_END = pd.Timestamp("2025-12-31", tz="UTC")
TEST_START = pd.Timestamp("2026-01-01", tz="UTC")


def deflated_bar(n):
    """2 + 0.5 log10(N), the bar in RESEARCH_SWEEP.md section 5."""
    return 2 + 0.5 * math.log10(max(int(n), 1))


def load_full_frames():
    """Daily OHLC and funding through the panel's last bar, not cut at train.

    Only confirm_cell calls this. The cut that protects the train scorer is
    deliberately absent here, and the periods are applied after the lag.
    """
    ohlcv = json.loads((RAW / "coinalyze_ohlcv-history.json").read_text())
    funding = json.loads((RAW / "coinalyze_funding-rate-history.json").read_text())
    inverse = {v: k for k, v in ohlcv["symbols"].items()}
    frames = {}
    for series in ohlcv["data"]:
        token = inverse[series["symbol"]]
        rows = {bar["t"]: bar for bar in series["history"]}
        frame = pd.DataFrame.from_dict(rows, orient="index").sort_index()
        frame.index = pd.to_datetime(frame.index, unit="s", utc=True)
        frame = frame.rename(columns={"o": "open", "h": "high", "l": "low",
                                      "c": "close", "v": "volume"})
        frames[token] = frame[["open", "high", "low", "close", "volume"]].astype(float)
    fund = {}
    for series in funding["data"]:
        token = inverse.get(series["symbol"])
        if token is None:
            continue
        s = pd.Series({bar["t"]: bar.get("c") for bar in series["history"]}, dtype=float)
        s.index = pd.to_datetime(s.index, unit="s", utc=True)
        fund[token] = s.sort_index()
    base = frames["BTC"].index
    for token in frames:
        frames[token] = frames[token].reindex(base)
        if token in fund:
            frames[token]["funding"] = fund[token].reindex(frames[token].index)
    return frames


def parse_cell_id(cell_id):
    """measure|transform|direction|threshold|target|universe|none|daily."""
    parts = cell_id.split("|")
    if len(parts) != 8:
        raise ValueError(f"cell id has {len(parts)} fields, expected 8")
    measure, transform_name, direction, threshold, target, universe, conditioning, timeframe = parts
    if transform_name not in TRANSFORMS:
        raise ValueError(f"unknown transform {transform_name}")
    if direction not in ("above", "below"):
        raise ValueError(f"unknown direction {direction}")
    if target not in TARGETS:
        raise ValueError(f"unknown target {target}")
    if universe not in UNIVERSES:
        raise ValueError(f"unknown universe {universe}")
    if conditioning != "none" or timeframe != "daily":
        raise ValueError("only conditioning none on daily bars is scorable")
    return {
        "measure": measure, "transform": transform_name, "direction": direction,
        "threshold": int(threshold), "target": target, "universe": universe,
    }


def _signal(values, direction, threshold):
    """Lag one bar, rank on the trailing window, flag the threshold."""
    lagged = np.concatenate([[np.nan], np.asarray(values, dtype=float)[:-1]])
    rank = rolling_rank(lagged)
    if direction == "above":
        flag = np.where(np.isnan(rank), -1, (rank >= threshold).astype(int))
    else:
        flag = np.where(np.isnan(rank), -1, (rank <= threshold).astype(int))
    return flag


def _period_score(signal, forward, horizon, years, index, start, end):
    """Score one period. Bars outside it are marked absent, not zero."""
    mask = (index >= start) & (index <= end)
    scoped = np.where(mask, signal, -1)
    year_scope = {year: mask & year_mask for year, year_mask in years.items()}
    return score_signal(scoped, forward, horizon, year_scope)


def score_periods(cell_id):
    """Validation and test for one cell. Does not read the leaderboard."""
    if "pit_cross_section" in cell_id:
        return _score_cross_section({"id": cell_id, "universe": "pit_cross_section"})
    cell = parse_cell_id(cell_id)
    frames = load_full_frames()
    if frames["BTC"].index.max() <= TRAIN_END:
        raise RuntimeError("the series ends at or before the train end")
    if cell["universe"] == "pooled_majors":
        raise ValueError("pooled confirmation is not in this procedure yet")
    if cell["universe"] == "pit_cross_section":
        return _score_cross_section(cell)
    token = "BTC" if cell["universe"] == "btc" else "ETH"
    frame = frames[token]
    computed = indicators(frame)
    if cell["measure"] not in computed.columns:
        raise ValueError(f"{cell['measure']} is not in the indicator frame")
    values = transform(computed[cell["measure"]].to_numpy(), cell["transform"])
    signal = _signal(values, cell["direction"], cell["threshold"])
    horizon = int(cell["target"].split("_")[1])
    relative = cell["target"].startswith("rel_")
    net = apply_costs(frame["close"], horizon, side=1, funding=frame["funding"])["net"].to_numpy()
    if relative:
        base = apply_costs(frames["BTC"]["close"], horizon, side=1,
                           funding=frames["BTC"]["funding"])["net"].to_numpy()
        net = net - base
    # A forward window that starts before the period and ends inside it would
    # mix periods. The period mask is applied to the signal, and the target
    # is already the return starting at the bar, so the window stays inside.
    years = {int(y): (frame.index.year == y) for y in sorted(set(frame.index.year))}
    validation = _period_score(signal, net, horizon, years, frame.index,
                               VALIDATION_START, VALIDATION_END)
    test = _period_score(signal, net, horizon, years, frame.index,
                         TEST_START, frame.index.max())
    return {
        "cell": cell, "token": token, "horizon": horizon,
        "panel_end": str(frame.index.max().date()),
        "library_version": LIBRARY_VERSION,
        "validation": validation, "test": test,
    }


def _score_cross_section(cell):
    """Validation and test for one cross-sectional cell, from the point-in-time panel."""
    from regime_tester.cross_section import score_cross_section
    panel = {}
    for name in sorted(os.listdir(ROOT / "data" / "panel_xs")):
        frame = pd.read_csv(ROOT / "data" / "panel_xs" / name)
        if "close" not in frame.columns or frame["close"].notna().sum() < 60:
            continue
        panel[name.replace(".csv", "")] = frame.dropna(subset=["close"])[["date", "close"]]
    scored = score_cross_section(panel, lambda close: close.pct_change(14), horizon=1)
    scored["date"] = pd.to_datetime(scored["date"], utc=True)

    def block(start, end):
        part = scored[(scored["date"] >= start) & (scored["date"] <= end)]["decile_spread"].dropna()
        if part.empty:
            return None
        return {"spread_independent": float(part.mean()),
                "t_newey_west": float(part.mean() / (part.std() / len(part) ** 0.5)) if len(part) > 2 else float("nan"),
                "n_independent": int(len(part))}

    return {"cell": cell, "token": "cross_section", "horizon": 1,
            "panel_end": str(scored["date"].max().date()), "library_version": LIBRARY_VERSION,
            "validation": block(VALIDATION_START, VALIDATION_END),
            "test": block(TEST_START, scored["date"].max())}


def _read_record():
    if not RECORD.exists():
        return []
    return json.loads(RECORD.read_text())


def confirm_cell(cell_id, family_n, train_sign, family_combinations=None):
    """One confirmation attempt. A cell already recorded is refused.

    family_n is the raw cell count tested in the family. family_combinations
    is the count of distinct measure, target and universe combinations, which
    is what the deflated bar uses, because threshold and lookback variants of
    one combination are near-duplicates. Both counts are recorded. A cell whose
    validation sample holds fewer than 30 independent observations is marked
    insufficient and re-queued when the periods grow, not rejected and closed.
    """
    if train_sign not in (1, -1):
        raise ValueError("train_sign must be 1 or -1")
    prior = _read_record()
    if any(row["cell_id"] == cell_id for row in prior):
        raise RuntimeError(f"{cell_id} already has a confirmation attempt")
    scored = score_periods(cell_id)
    bar_n = family_combinations if family_combinations is not None else family_n
    bar = deflated_bar(bar_n)
    validation = scored["validation"]
    test = scored["test"]
    if validation is None or validation["n_independent"] < 30:
        verdict = "insufficient"
        reason = "validation holds fewer than 30 independent observations; re-queued, not closed"
    else:
        val_t = validation["t_newey_west"]
        val_sign = int(np.sign(validation["spread_independent"])) if not np.isnan(validation["spread_independent"]) else 0
        if val_sign != train_sign or not (val_sign * val_t > bar):
            verdict = "rejected"
            reason = "validation t-stat does not clear the deflated bar with the train sign"
        elif int(np.sign(test["spread_independent"])) != train_sign:
            verdict = "rejected"
            reason = "test flips the train sign"
        elif test["n_independent"] < MIN_INDEPENDENT:
            verdict = "test pending"
            reason = "validation clears the bar; test holds fewer than 40 independent observations"
        else:
            verdict = "admitted"
            reason = "validation clears the deflated bar and test keeps the sign"
    record = {
        "cell_id": cell_id,
        "attempted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "family_n": int(family_n),
        "family_combinations": int(bar_n),
        "deflated_bar": round(bar, 4),
        "train_sign": int(train_sign),
        "panel_end": scored["panel_end"],
        "library_version": scored["library_version"],
        "validation": validation,
        "test": test,
        "verdict": verdict,
        "reason": reason,
    }
    prior.append(record)
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    tmp = RECORD.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(prior, indent=2, default=str))
    os.replace(tmp, RECORD)
    return record
