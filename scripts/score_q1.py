"""Score the pre-registered Q1 cells for BTC and ETH.

The rules are research/outside/PREREG_Q1.md, committed before this script
existed. The pooled panel is not scored here: reading every file in
data/panel_xs_laevitas does not finish inside a research run, and the
pre-registration says so.
"""

import json
import os
import subprocess
import sys

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREREG = "research/outside/PREREG_Q1.md"
PANEL = os.path.join(ROOT, "data", "panel_xs_laevitas")
VAL_START, VAL_END = "2024-07-01", "2025-12-31"
TEST_START = "2026-01-01"
CUT = 0.8
WINDOWS = (10, 20, 30)
CRASH = -0.10
EPISODE_BAR = 20
PERCENTILE_WINDOW = 365
PERCENTILE_MIN = 252
ASSETS = {"BTC": "binance_BTCUSDT.csv", "ETH": "binance_ETHUSDT.csv"}


def prereg_commit():
    added = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=%H", "--", PREREG],
        cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    if len(added) != 1:
        raise SystemExit(f"pre-registration was added in {len(added)} commits")
    commit = added[0]
    if subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"],
                      cwd=ROOT).returncode != 0:
        raise SystemExit("pre-registration commit is not an ancestor of HEAD")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
        check=True).stdout.strip()
    if head == commit:
        raise SystemExit("scoring in the same commit as the pre-registration")
    return commit


def load_asset(name):
    frame = pd.read_csv(os.path.join(PANEL, ASSETS[name]))
    frame["date"] = pd.to_datetime(frame["date"], utc=True)
    frame = frame.drop_duplicates("date").set_index("date").sort_index()
    return frame["close"].astype(float), frame["long_short_ratio"].astype(float)


def trailing_percentile(series):
    values = series.to_numpy(dtype=float)
    out = np.full(len(values), np.nan)
    for i in range(len(values)):
        if np.isnan(values[i]):
            continue
        history = values[max(0, i - PERCENTILE_WINDOW):i]
        history = history[~np.isnan(history)]
        if len(history) < PERCENTILE_MIN:
            continue
        out[i] = np.mean(history <= values[i])
    return pd.Series(out, index=series.index)


def forward_drawdown(price, horizon):
    """Worst close within the next `horizon` bars, against today's close."""
    values = price.to_numpy(dtype=float)
    out = np.full(len(values), np.nan)
    for i in range(len(values) - horizon):
        window = values[i + 1:i + 1 + horizon]
        if np.isnan(values[i]) or np.isnan(window).any():
            continue
        out[i] = np.min(window) / values[i] - 1
    return pd.Series(out, index=price.index)


def forward_return(price, horizon):
    return price.shift(-horizon) / price - 1


def period_of(index):
    dates = pd.Series(pd.to_datetime(index).strftime("%Y-%m-%d"), index=index)
    out = pd.Series("train", index=index)
    out[(dates >= VAL_START) & (dates <= VAL_END)] = "validation"
    out[dates >= TEST_START] = "test"
    return out


def episodes(flag):
    flagged = flag.fillna(False).astype(bool)
    starts = flagged & ~flagged.shift(1, fill_value=False)
    which = period_of(flag.index)
    return {name: int((starts & (which == name)).sum())
            for name in ("train", "validation", "test")}


def score_window(flag, drawdown, ret20):
    which = period_of(flag.index)
    rows = {}
    for name in ("train", "validation", "test"):
        mask = (which == name) & flag.notna() & drawdown.notna()
        flagged = flag[mask].fillna(False).astype(bool)
        dd = drawdown[mask]
        row = {"n": int(len(dd)), "flagged": int(flagged.sum())}
        if flagged.sum() >= 3:
            row["drawdown_effect"] = round(float(dd[flagged].mean() - dd.mean()), 6)
            crash_flag = float((dd[flagged] <= CRASH).mean())
            crash_all = float((dd <= CRASH).mean())
            row["crash_lift"] = round(crash_flag / crash_all, 6) if crash_all else None
            fwd = ret20[mask]
            row["false_alarm"] = round(float((fwd[flagged] > 0).mean()), 6)
        rows[name] = row
    return rows


def verdict_of(rows, counts):
    held = [rows.get(name, {}) for name in ("validation", "test")]
    if any("drawdown_effect" not in row for row in held):
        return "insufficient"
    if counts["train"] + counts["validation"] < EPISODE_BAR:
        return "insufficient"
    signs = [row["drawdown_effect"] < 0 for row in held]
    if signs[0] != signs[1]:
        return "rejected"
    return "kept"


def lookahead(ratio):
    """Perturbing the ratio after day t leaves the rank at t unchanged."""
    rank = trailing_percentile(ratio.shift(1))
    cut = rank.index[len(rank) // 2]
    perturbed = ratio.copy()
    perturbed[perturbed.index > cut] = perturbed[perturbed.index > cut] * 1.5 + 3
    after = trailing_percentile(perturbed.shift(1))
    before = rank[rank.index <= cut].to_numpy(dtype=float)
    return bool(np.allclose(before, after.reindex(rank[rank.index <= cut].index).to_numpy(dtype=float),
                            equal_nan=True))


def main():
    commit = prereg_commit()
    cells = []
    passed = {}
    for asset in ASSETS:
        close, ratio = load_asset(asset)
        rank = trailing_percentile(ratio.shift(1))
        flag = rank.ge(CUT).where(rank.notna())
        counts = episodes(flag)
        passed[asset] = lookahead(ratio)
        for window in WINDOWS:
            rows = score_window(flag, forward_drawdown(close, window),
                                forward_return(close, 20))
            cells.append({
                "asset": asset, "window": window, "episodes": counts,
                "periods": rows, "verdict": verdict_of(rows, counts),
            })
    payload = {
        "prereg_commit": commit,
        "pooled": "not scored; the panel read does not finish in a research run",
        "lookahead_passed": passed,
        "cells": cells,
    }
    path = write_result("q1_lsr_drawdown", payload,
                        inputs=["data/panel_xs_laevitas", PREREG])
    print(json.dumps({"path": path, "lookahead": passed,
                      "verdicts": [c["verdict"] for c in cells]}))


if __name__ == "__main__":
    main()
