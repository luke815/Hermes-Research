"""S2 cell enumerator.

Writes results/sweeps/space.json: every cell the search space in
RESEARCH_SWEEP.md section 3 produces from the indicator library, with the
count of cells that cannot meet their minimum history or minimum episode
count on the train period stated separately as skipped.

This script counts. It does not score a return and it does not read
validation or test.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from regime_tester.indicators import LIBRARY_VERSION, META  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "panel.csv"
OUT = ROOT / "results" / "sweeps" / "space.json"

# Grids, fixed by RESEARCH_SWEEP.md section 3. A change here is a change to
# the search space and must be versioned, not tuned.
TRANSFORMS = [
    "raw", "pct_252", "z_30", "z_90", "chg_3", "chg_7", "chg_30",
    "persistence", "acceleration", "divergence_20", "xs_rank", "ratio_btc",
]
# Crossover pairs that make sense: price against its averages, and the fast
# average against the slow one. These are events, not thresholded measures.
CROSSOVERS = [
    ("close", "sma_20"), ("close", "sma_50"), ("close", "sma_200"),
    ("sma_50", "sma_200"),
]
# Thresholds are trailing percentiles, so "above the 80th" and "below the
# 20th" are the two directions at three cuts each.
THRESHOLDS = [80, 90, 95, 20, 10, 5]
TARGETS_DAILY = ["ret_1", "ret_3", "ret_10", "rel_1", "rel_3", "rel_10",
                 "top_T30_20", "bottom_B30_20_7"]
TARGETS_INTRADAY = ["ret_4", "ret_12", "ret_24", "rel_4", "rel_12", "rel_24"]
UNIVERSES = ["btc", "eth", "pooled_majors", "pit_cross_section"]
CONDITIONING = ["none", "heat_tercile", "rvol_tercile", "trend_state",
                "admitted_extreme"]
TIMEFRAMES = ["daily", "4h", "1h"]

TRAIN_END = "2024-06-30"
# Event cells need 30 episodes across train and validation combined. Train is
# the only period the sweep may read, so a cell that cannot reach 15 episodes
# on train alone is counted as skipped.
MIN_EPISODES_TRAIN = 15
# A return cell needs 40 independent observations. With a 10-bar horizon that
# is 400 bars of usable history after the indicator's own minimum.
MIN_INDEPENDENT = 40


def panel_facts():
    """What the panel can actually serve, read from the file, not assumed."""
    df = pd.read_csv(PANEL)
    date_col = "date" if "date" in df.columns else df.columns[0]
    dates = pd.to_datetime(df[date_col], utc=True)
    train = dates[dates <= TRAIN_END]
    return {
        "panel_rows": int(len(df)),
        "panel_end": str(dates.max().date()),
        "train_rows": int(len(train)),
        "train_start": str(train.min().date()) if len(train) else None,
        "columns": sorted(df.columns),
        "pit_names": pit_names(),
        "pooled_episodes": True,
    }


def pit_names():
    """Names in the point-in-time panel with price history before the train end.

    The cross-section is only real if enough names reach back past the train
    end. Below 30 it is treated as absent, and the cross-sectional cells stay
    skipped rather than being scored on a handful of names.
    """
    count = 0
    for name in os.listdir(ROOT / "data" / "panel_xs"):
        frame = pd.read_csv(ROOT / "data" / "panel_xs" / name,
                            usecols=lambda c: c in ("date", "close"))
        if ("close" in frame.columns and frame["close"].notna().any()
                and frame["date"].min() < TRAIN_END):
            count += 1
    return count if count >= 30 else 0


def bars_available(timeframe, facts):
    """Bars of history the stores hold for a timeframe.

    Daily comes from the panel. The 4-hour and hourly stores are not built
    yet (D4 and the intraday store cover the live window only), so those
    timeframes are enumerated but every cell on them is skipped.
    """
    if timeframe == "daily":
        return facts["train_rows"]
    return 0


def targets_for(timeframe):
    """Daily bars carry the daily targets; intraday bars carry only their own.

    The amended top and bottom events are defined on daily closes, so they are
    daily cells only.
    """
    if timeframe == "daily":
        return TARGETS_DAILY
    return TARGETS_INTRADAY


def cell_id(parts):
    return "|".join(str(p) for p in parts)


def enumerate_cells(facts):
    cells = []
    for name, (family, inputs, min_history, kind) in META.items():
        measures = [(name, t) for t in TRANSFORMS]
        for transform in TRANSFORMS:
            for threshold in THRESHOLDS:
                direction = "below" if threshold <= 20 else "above"
                for timeframe in TIMEFRAMES:
                    for target in targets_for(timeframe):
                        for universe in UNIVERSES:
                            for conditioning in CONDITIONING:
                                cells.append(make(
                                    name, family, inputs, min_history, kind,
                                    transform, direction, threshold, target,
                                    universe, conditioning, timeframe, facts))
    for fast, slow in CROSSOVERS:
        family = "trend"
        min_history = META.get(slow, ("trend", ["close"], 200, "level"))[2]
        for timeframe in TIMEFRAMES:
            for target in targets_for(timeframe):
                for universe in UNIVERSES:
                    for conditioning in CONDITIONING:
                        cells.append(make(
                            f"xover_{fast}_{slow}", family, ["close"], min_history,
                            "flag", "crossover", "cross", 0, target, universe,
                            conditioning, timeframe, facts))
    return cells


def make(measure, family, inputs, min_history, kind, transform, direction,
         threshold, target, universe, conditioning, timeframe, facts):
    available = bars_available(timeframe, facts)
    reasons = []
    if timeframe != "daily":
        reasons.append("no_store")
    if available < min_history + MIN_INDEPENDENT:
        reasons.append("min_history")
    if target.startswith("top_") or target.startswith("bottom_"):
        # BTC and ETH alone hold too few episodes. The pooled panel clears
        # the bar, so event cells are testable there and only there.
        if universe != "pooled_majors" or not facts.get("pooled_episodes"):
            reasons.append("min_episodes")
    if universe == "pit_cross_section" and not facts.get("pit_names"):
        reasons.append("no_pit_universe")
    if "funding" in inputs and timeframe == "daily" and "funding" not in "".join(facts["columns"]):
        reasons.append("missing_input")
    skipped = bool(reasons)
    return {
        "id": cell_id([measure, transform, direction, threshold, target,
                       universe, conditioning, timeframe]),
        "measure": measure,
        "family": family,
        "inputs": inputs,
        "min_history": min_history,
        "kind": kind,
        "transform": transform,
        "direction": direction,
        "threshold": threshold,
        "target": target,
        "universe": universe,
        "conditioning": conditioning,
        "timeframe": timeframe,
        "status": "skipped" if skipped else "testable",
        "skip_reasons": reasons,
    }


def summarize(cells):
    by_family = {}
    for c in cells:
        slot = by_family.setdefault(c["family"], {"cells": 0, "testable": 0, "skipped": 0})
        slot["cells"] += 1
        slot["skipped" if c["status"] == "skipped" else "testable"] += 1
    reasons = {}
    for c in cells:
        for r in c["skip_reasons"]:
            reasons[r] = reasons.get(r, 0) + 1
    ids = [c["id"] for c in cells]
    return {
        "by_family": dict(sorted(by_family.items())),
        "skip_reasons": dict(sorted(reasons.items())),
        "duplicate_ids": len(ids) - len(set(ids)),
    }


def main():
    facts = panel_facts()
    cells = enumerate_cells(facts)
    summary = summarize(cells)
    total = len(cells)
    skipped = sum(1 for c in cells if c["status"] == "skipped")
    assert total == sum(v["cells"] for v in summary["by_family"].values()), "counts do not add up"
    assert summary["duplicate_ids"] == 0, "a cell is counted twice"
    payload = {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "library_version": LIBRARY_VERSION,
        "train_end": TRAIN_END,
        "panel": facts,
        "grids": {
            "transforms": TRANSFORMS,
            "crossovers": [f"{a}_x_{b}" for a, b in CROSSOVERS],
            "thresholds": THRESHOLDS,
            "targets_daily": TARGETS_DAILY,
            "targets_intraday": TARGETS_INTRADAY,
            "universes": UNIVERSES,
            "conditioning": CONDITIONING,
            "timeframes": TIMEFRAMES,
        },
        "cells": total,
        "testable": total - skipped,
        "skipped": skipped,
        "by_family": summary["by_family"],
        "skip_reasons": summary["skip_reasons"],
        "duplicate_ids": summary["duplicate_ids"],
        "cell_ids_sample": [c["id"] for c in cells[:3]],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2))
    print(json.dumps({k: payload[k] for k in
                      ("cells", "testable", "skipped", "duplicate_ids", "by_family", "skip_reasons")}))


if __name__ == "__main__":
    main()
