"""Score the pre-registered weekly cycle layer.

The rule is research/outside/PREREG_C10.md, committed before this script
existed. The script reads that commit and refuses to score when it is not an
ancestor of HEAD, so a rule edited in the scoring commit is not
pre-registered.

Weekly bars are the Sunday close of the daily panel. The signal at week t
uses the prior week's close, so week t itself never enters. The labels look
forward and are never features.
"""

import os
import subprocess
import sys

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.episodes import bottom_event, episodes, top_event  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREREG = "research/outside/PREREG_C10.md"
PANEL = os.path.join(ROOT, "data", "panel.csv")
TRAIN_END = "2024-06-30"
VAL_END = "2025-12-31"
HORIZONS = (12, 26)
WINDOW = 52
TOP_GAP = 0.05
BOTTOM_GAP = 0.40
TOP_DRAWDOWN = 0.25
BOTTOM_RALLY = 0.30
BOTTOM_GIVEBACK = 0.10
EPISODE_BAR = 30
ASSETS = ("btc", "eth")


def prereg_commit():
    """The commit that added the pre-registration. It must precede HEAD."""
    added = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=%H", "--", PREREG],
        cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    if len(added) != 1:
        raise SystemExit(f"pre-registration was added in {len(added)} commits")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
        check=True).stdout.strip()
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", added[0], head], cwd=ROOT)
    if ancestor.returncode != 0:
        raise SystemExit("pre-registration commit is not an ancestor of HEAD")
    return added[0]


def episode_count(label):
    """Runs of consecutive true weeks, which is the honest sample size."""
    ids = episodes(label)
    return int(ids[ids > 0].nunique())


def weekly_close(daily):
    """Sunday close. A week is kept only when its Sunday is in the panel."""
    frame = daily.copy()
    frame.index = pd.to_datetime(frame.index)
    sunday = frame.index.to_series().dt.to_period("W-SUN").dt.end_time.dt.normalize()
    grouped = frame.groupby(sunday)
    last_day = grouped.apply(lambda part: part.index.max()).dt.tz_convert("UTC")
    boundary = pd.DatetimeIndex(last_day.index).tz_localize("UTC")
    kept = last_day[last_day == boundary]
    return grouped.last().loc[kept.index]


def ratio(close, window):
    """Close over its trailing window high, lagged one bar."""
    high = close.rolling(window, min_periods=window).max().shift(1)
    return close.shift(1) / high


def period_of(dates):
    out = []
    for day in dates:
        stamp = str(day)[:10]
        if stamp <= TRAIN_END:
            out.append("train")
        elif stamp <= VAL_END:
            out.append("validation")
        else:
            out.append("test")
    return out


def lift(flag, label):
    """Episode lift and the episode counts, per period."""
    rows = {}
    periods = period_of(flag.index)
    for name in ("train", "validation", "test"):
        mask = np.array([period == name for period in periods])
        flagged = flag[mask]
        labelled = label[mask]
        base = episode_count(labelled)
        fired = episode_count(labelled & flagged)
        false = episode_count(flagged & ~labelled)
        rows[name] = {
            "episodes_flagged": int(episode_count(flagged)),
            "episodes_labelled": int(base),
            "episodes_both": int(fired),
            "episodes_false": int(false),
            "lift": None if base == 0 else round(fired / base, 4),
        }
    return rows


def verdict(rows):
    train_val = rows["train"]["episodes_both"] + rows["validation"]["episodes_both"]
    if train_val < EPISODE_BAR:
        return "insufficient"
    signs = []
    for name in ("validation", "test"):
        value = rows[name]["lift"]
        if value is None:
            return "insufficient"
        signs.append(value - 1)
    if signs[0] == 0 or signs[1] == 0 or (signs[0] > 0) != (signs[1] > 0):
        return "rejected"
    return "kept"


def main():
    commit = prereg_commit()
    daily = pd.read_csv(PANEL, index_col=0, parse_dates=True)
    cells = []
    for asset in ASSETS:
        close = weekly_close(daily[f"{asset}_price"].dropna())
        signal = ratio(close, WINDOW)
        for horizon in HORIZONS:
            top = top_event(close, horizon, TOP_DRAWDOWN)
            bottom = bottom_event(close, horizon, BOTTOM_RALLY, BOTTOM_GIVEBACK)
            for side, flag, label in (
                    ("top", signal <= TOP_GAP, top),
                    ("bottom", signal >= BOTTOM_GAP, bottom)):
                usable = flag.notna() & label.notna()
                rows = lift(flag[usable].astype(bool), label[usable].astype(bool))
                cells.append({
                    "asset": asset,
                    "side": side,
                    "horizon_weeks": horizon,
                    "weekly_bars": int(usable.sum()),
                    "periods": rows,
                    "verdict": verdict(rows),
                })
    payload = {
        "item": "C10",
        "prereg_commit": commit,
        "panel": "data/panel.csv",
        "weekly_rule": "Sunday close, trailing 52-week high, lagged one bar",
        "cells": cells,
        "verdict": "insufficient" if any(
            cell["verdict"] == "insufficient" for cell in cells) else "recorded",
    }
    path = write_result("c10_weekly", payload, inputs=["data/panel.csv", PREREG])
    print(path)


if __name__ == "__main__":
    main()
