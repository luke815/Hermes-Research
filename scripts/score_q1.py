"""Score the pre-registered Q1 cells for BTC, ETH and the pooled panel.

The rules are research/outside/PREREG_Q1.md, committed before this script
existed. The pooled panel uses the same rule and the same bar: one row per
base coin, the venue with the most days, a name in on a date only when its
file has a close that date. The pooled reading is the equal-weight mean of
the names whose signal is defined that day, and a missing ratio leaves the
name out rather than filling it.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

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


def base_of(symbol):
    """Strip the quote and the venue suffix so the same coin collapses."""
    stem = symbol.split(".")[0]
    for suffix in ("_PERP", "-SWAP", "USDT", "USDC", "USD"):
        if stem.endswith(suffix) and len(stem) > len(suffix):
            stem = stem[: -len(suffix)]
            break
    return stem


def load_pooled():
    """Close and long/short ratio, one column per base coin.

    The longest file wins for a coin. A name is present on a date only when
    its file has a close that date. Nothing is filled forward.
    """
    best = {}
    lengths = {}
    for path in sorted(Path(PANEL).glob("*.csv")):
        symbol = path.name.split("_", 1)[1][:-4]
        header = path.read_text(encoding="utf-8").split("\n", 1)[0].split(",")
        if "close" not in header or "long_short_ratio" not in header:
            continue
        frame = pd.read_csv(path, usecols=["date", "close", "long_short_ratio"])
        frame = frame.dropna(subset=["close"])
        if frame.empty:
            continue
        frame["date"] = pd.to_datetime(frame["date"], utc=True).dt.normalize()
        frame = frame.drop_duplicates("date").set_index("date").sort_index()
        frame = frame[frame["close"].astype(float) > 0]
        if frame.empty:
            continue
        key = base_of(symbol)
        if len(frame) > lengths.get(key, -1):
            best[key] = frame
            lengths[key] = len(frame)
    if "BTC" not in best:
        raise SystemExit("BTC is not in the panel")
    dates = pd.DatetimeIndex(sorted(set().union(*(f.index for f in best.values()))))
    pos = {d: i for i, d in enumerate(dates)}
    names = sorted(best)
    close_a = np.full((len(dates), len(names)), np.nan)
    ratio_a = np.full((len(dates), len(names)), np.nan)
    for j, name in enumerate(names):
        frame = best[name]
        rows = np.fromiter((pos[d] for d in frame.index), dtype=int, count=len(frame))
        close_a[rows, j] = frame["close"].to_numpy(dtype=float)
        ratio_a[rows, j] = frame["long_short_ratio"].to_numpy(dtype=float)
    close = pd.DataFrame(close_a, index=dates, columns=names)
    ratio = pd.DataFrame(ratio_a, index=dates, columns=names)
    return close, ratio


def trailing_percentile(series):
    """Rank of each value against the preceding window, the current bar excluded.

    A trailing window cannot see the bar it ranks, and a history shorter than
    the minimum stays empty. The same rule applies to one series and to a
    panel of them.
    """
    values = series.to_numpy(dtype=float)
    if values.ndim == 1:
        values = values.reshape(-1, 1)
    length, columns = values.shape
    out = np.full(values.shape, np.nan)
    for i in range(PERCENTILE_MIN, length):
        history = values[max(0, i - PERCENTILE_WINDOW):i]
        current = values[i]
        known = ~np.isnan(history)
        count = known.sum(axis=0)
        below = (known & (history <= current)).sum(axis=0)
        present = ~np.isnan(current) & (count >= PERCENTILE_MIN)
        out[i, present] = below[present] / count[present]
    out = out[:, 0] if series.ndim == 1 else out
    return pd.Series(out, index=series.index) if series.ndim == 1 else pd.DataFrame(
        out, index=series.index, columns=series.columns)


def forward_drawdown(price, horizon):
    """Worst close within the next `horizon` bars, against today's close."""
    values = price.to_numpy(dtype=float)
    single = values.ndim == 1
    if single:
        values = values.reshape(-1, 1)
    out = np.full(values.shape, np.nan)
    for i in range(len(values) - horizon):
        window = values[i + 1:i + 1 + horizon]
        base = values[i]
        complete = ~np.isnan(base) & ~np.isnan(window).any(axis=0)
        worst = np.min(np.where(np.isnan(window), np.inf, window), axis=0)
        out[i, complete] = worst[complete] / base[complete] - 1
    out = out[:, 0] if single else out
    return pd.Series(out, index=price.index) if single else pd.DataFrame(
        out, index=price.index, columns=price.columns)


def forward_return(price, horizon):
    return price.shift(-horizon) / price - 1


def pooled_mean(frame, defined):
    """Equal-weight mean of the names whose signal is defined that day."""
    masked = frame.where(defined)
    count = masked.notna().sum(axis=1)
    return masked.mean(axis=1).where(count > 0)


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
    pooled_close, pooled_ratio = load_pooled()
    pooled_rank = trailing_percentile(pooled_ratio.shift(1))
    pooled_flag = pooled_rank.ge(CUT).where(pooled_rank.notna())
    defined = pooled_rank.notna()
    breadth = pooled_flag.fillna(False).astype(bool).mean(axis=1).where(defined.any(axis=1))
    pooled_flagged = breadth.ge(0.5).where(breadth.notna())
    pooled_counts = episodes(pooled_flagged)
    passed["pooled"] = lookahead(pooled_ratio["BTC"])
    for window in WINDOWS:
        drawdown = pooled_mean(forward_drawdown(pooled_close, window), defined)
        ret20 = pooled_mean(forward_return(pooled_close, 20), defined)
        rows = score_window(pooled_flagged, drawdown, ret20)
        cells.append({
            "asset": "pooled", "window": window, "episodes": pooled_counts,
            "names": int(pooled_close.shape[1]),
            "breadth": "share of defined names flagged, flagged when at least half are",
            "periods": rows, "verdict": verdict_of(rows, pooled_counts),
        })
    payload = {
        "prereg_commit": commit,
        "pooled_names": int(pooled_close.shape[1]),
        "lookahead_passed": passed,
        "cells": cells,
    }
    path = write_result("q1_lsr_drawdown", payload,
                        inputs=["data/panel_xs_laevitas", PREREG])
    print(json.dumps({"path": path, "lookahead": passed,
                      "verdicts": [c["verdict"] for c in cells],
                      "names": int(pooled_close.shape[1])}))


if __name__ == "__main__":
    main()
