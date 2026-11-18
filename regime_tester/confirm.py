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


XS_TRANSFORMS = TRANSFORMS + ["xs_rank", "divergence_20", "ratio_btc"]
XS_TARGETS = ["ret_1", "ret_3", "ret_10"]


def parse_cell_id(cell_id):
    """measure|transform|direction|threshold|target|universe|none|daily."""
    parts = cell_id.split("|")
    if len(parts) != 8:
        raise ValueError(f"cell id has {len(parts)} fields, expected 8")
    measure, transform_name, direction, threshold, target, universe, conditioning, timeframe = parts
    cross = universe == "pit_cross_section"
    allowed_transforms = XS_TRANSFORMS if cross else TRANSFORMS
    allowed_targets = XS_TARGETS if cross else TARGETS
    if transform_name not in allowed_transforms:
        raise ValueError(f"unknown transform {transform_name}")
    if direction not in ("above", "below"):
        raise ValueError(f"unknown direction {direction}")
    if target not in allowed_targets:
        raise ValueError(f"unknown target {target}")
    if not cross and universe not in UNIVERSES:
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


def hac_t(values, lag):
    """t-stat of a mean. Overlapping windows use HAC with lag at least the horizon.

    A lag of 1 is a non-overlapping sample, and the result is written as
    t_newey_west. Any other lag is not that statistic, so the caller writes it
    under hac_t instead.
    """
    stat = newey_west_t(np.asarray(values, dtype=float), max(int(lag), 1))
    return {"t_newey_west": float(stat)} if int(lag) <= 1 else {"hac_t": float(stat)}


def family_of(cell_id):
    """The indicator family a confirmation attempt counts against."""
    from regime_tester.indicators import META
    measure = cell_id.split("|")[0]
    return META[measure][0] if measure in META else "unlisted"


def family_attempts(record=None):
    """Validation attempts already recorded in each family. The count only rises."""
    rows = _read_record() if record is None else record
    counts = {}
    for row in rows:
        if row.get("validation") is None:
            continue
        family = row.get("family") or family_of(row["cell_id"])
        counts[family] = counts.get(family, 0) + 1
    return counts


# The thin tier the sweep charges, 5 bps fee plus 10 bps slippage, each way.
XS_COST_BPS = 15


def _xs_net_panel(panel, horizon):
    """Forward return net of two times the sweep's thin-tier cost, per name.

    Two times, because a cross-sectional spread is a long and a short, and
    each pays the round trip. The sweep charges 15 bps a side, so the spread
    loses 30 bps. A funding column that is present but blank leaves the net
    missing rather than treating the carry as zero. A frame with no funding
    column has no carry to charge.
    """
    from regime_tester.costs import apply_costs
    out = {}
    for name, frame in panel.items():
        indexed = frame.set_index("date") if "date" in frame.columns else frame
        close = indexed["close"].astype(float)
        close.index = pd.to_datetime(close.index, utc=True)
        column = next((c for c in ("funding", "funding_rate") if c in indexed.columns), None)
        funding = indexed[column].astype(float) if column else pd.Series(0.0, index=close.index)
        funding.index = close.index
        net = apply_costs(close, horizon, side=1, funding=funding)["gross"]
        carry = funding.rolling(horizon, min_periods=horizon).sum().shift(-(horizon - 1)) / 100
        net = net - carry.fillna(0 if column is None else np.nan)
        net = net - 2 * XS_COST_BPS / 10_000
        out[name] = net
    return out


def score_periods(cell_id, panel=None):
    """Validation and test for one cell. Does not read the leaderboard."""
    cell = parse_cell_id(cell_id)
    if cell["universe"] == "pit_cross_section":
        return _score_cross_section(cell, panel)
    frames = load_full_frames()
    if frames["BTC"].index.max() <= TRAIN_END:
        raise RuntimeError("the series ends at or before the train end")
    if cell["universe"] == "pooled_majors":
        raise ValueError("pooled confirmation is not in this procedure yet")
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


def _xs_signal(close, cell):
    """The cell's own measure and transform, lagged one bar by the scorer."""
    from regime_tester.indicators import indicators
    frame = close.to_frame("close") if isinstance(close, pd.Series) else close
    built = indicators(frame)
    measure = cell["measure"]
    values = built[measure] if measure in built.columns else close * np.nan
    return pd.Series(
        transform(values.to_numpy(dtype=float), cell["transform"]), index=values.index)


def _load_cross_batch(names):
    """One batch of the Laevitas panel. Loading every file takes minutes."""
    from regime_tester.panel_integrity import clean_frame
    source = ROOT / "data" / "panel_xs_laevitas"
    if not source.exists():
        source = ROOT / "data" / "panel_xs"
    panel = {}
    for name in names:
        frame = clean_frame(pd.read_csv(source / f"{name}.csv"))
        if "close" not in frame.columns or frame["close"].notna().sum() < 60:
            continue
        panel[name] = frame.dropna(subset=["close"])
    return panel


def _score_cross_section(cell, panel=None, names=None):
    """Validation and test for one cross-sectional cell, built from its own id.

    rel_ targets are not scored: subtracting BTC cancels inside a same-day
    rank, so a rel_ cell is the same test as its ret_ twin. names limits the
    score to those coins, so a daemon can score one batch and resume. The
    spread is the daily long-short spread of the names the cell flags, and its
    t-stat is HAC with lag at least the horizon. t_newey_west is written only
    for lag 1.
    """
    from regime_tester.cross_section import decile_spread
    if cell["target"].startswith("rel_"):
        raise ValueError("rel_ cross-sectional targets are dropped; they equal ret_")
    horizon = int(cell["target"].split("_")[1])
    if panel is None:
        raise ValueError("a cross-sectional score needs a panel; pass one batch")
    elif names is not None:
        panel = {name: frame for name, frame in panel.items() if name in names}
    rows = []
    for name, frame in panel.items():
        indexed = frame.set_index("date") if "date" in frame.columns else frame
        close = indexed["close"].astype(float)
        close.index = pd.to_datetime(close.index, utc=True)
        signal = _xs_signal(indexed, cell)
        signal.index = pd.to_datetime(signal.index, utc=True)
        signal = signal.shift(1)
        if signal.notna().sum() == 0:
            continue
        forward = _xs_net_panel({name: frame}, horizon)[name]
        joined = pd.DataFrame({"signal": signal, "forward": forward}).dropna()
        joined["name"] = name
        rows.append(joined)
    if not rows:
        raise RuntimeError("the cross-sectional panel has no scorable names")
    stacked = pd.concat(rows)
    daily = []
    for date, group in stacked.groupby(level=0):
        if not hasattr(date, "year"):
            continue
        daily.append({"date": date, "spread": decile_spread(group["signal"], group["forward"])})
    scored = pd.DataFrame(daily, columns=["date", "spread"])
    if scored.empty:
        raise RuntimeError("the cross-sectional panel has no dated spreads")
    scored["date"] = pd.to_datetime(scored["date"], utc=True)

    def block(start, end):
        part = scored[(scored["date"] >= start) & (scored["date"] <= end)]["spread"].dropna()
        if part.empty:
            return None
        stats = hac_t(part.to_numpy(), horizon)
        return {"spread_independent": float(part.iloc[::horizon].mean()),
                "n_independent": int(len(part.iloc[::horizon])), **stats}

    return {"cell": cell, "token": "cross_section", "horizon": horizon,
            "panel_end": str(scored["date"].max().date()), "library_version": LIBRARY_VERSION,
            "validation": block(VALIDATION_START, VALIDATION_END),
            "test": block(TEST_START, scored["date"].max())}


def _read_record():
    if not RECORD.exists():
        return []
    return json.loads(RECORD.read_text())


def confirm_cell(cell_id, family_n, train_sign, family_combinations=None, panel=None):
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
    # A void row is not an attempt. The pre-fix scorer wrote a verdict the
    # current method would not produce, so a void cell is scored again.
    if any(row["cell_id"] == cell_id and not str(row.get("verdict", "")).startswith("void")
           for row in prior):
        raise RuntimeError(f"{cell_id} already has a confirmation attempt")
    try:
        scored = score_periods(cell_id, panel)
    except (ValueError, RuntimeError) as exc:
        if "pit_cross_section" not in cell_id:
            raise
        record = {
            "cell_id": cell_id,
            "attempted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "verdict": "void",
            "void_reason": f"{type(exc).__name__}: {exc}",
        }
        prior.append(record)
        RECORD.parent.mkdir(parents=True, exist_ok=True)
        tmp = RECORD.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(prior, indent=2, default=str))
        os.replace(tmp, RECORD)
        return record
    family = family_of(cell_id)
    attempts = family_attempts(prior)
    bar_n = attempts.get(family, 0) + 1
    if family_n is not None and int(family_n) > bar_n:
        bar_n = int(family_n)
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
        "family": family,
        "family_n": int(bar_n),
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
