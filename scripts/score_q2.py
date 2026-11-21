"""Score the pre-registered Q2 cells for BTC and ETH.

The rules are research/outside/PREREG_Q2.md, committed before this script
existed. The sign is confirmed only on 2019-03 to 2020-01 and on 2026. The
years 2020 to 2025 are reported and are not used for the verdict.
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
PREREG = "research/outside/PREREG_Q2.md"
MARKET = os.path.join(ROOT, "data", "laevitas", "market")
PANEL = os.path.join(ROOT, "data", "panel.csv")
SKEW_CUT = 0.9
DVOL_CUT = 0.2
HORIZONS = (5, 10, 20)
WINDOWS = (10, 20)
EPISODE_BAR = 20
PERCENTILE_WINDOW = 365
PERCENTILE_MIN = 252
ASSETS = ("BTC", "ETH")
FRESH = (
    ("2019-03 to 2020-01", "2019-03-01", "2020-01-31"),
    ("2026", "2026-01-01", None),
)
REPORTED = ("2020-2025", "2020-02-01", "2025-12-31")


def prereg_commit():
    added = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=%H", "--", PREREG],
        cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    if len(added) != 1:
        raise SystemExit(f"pre-registration was added in {len(added)} commits")
    commit = added[0]
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
        check=True).stdout.strip()
    if head == commit:
        raise SystemExit("scoring in the same commit as the pre-registration")
    return commit


def market(prefix):
    rows = []
    for name in sorted(os.listdir(MARKET)):
        if name.startswith(prefix):
            rows.extend(json.load(open(os.path.join(MARKET, name))).get("items", []))
    frame = pd.DataFrame(rows).drop_duplicates("date", keep="last")
    frame["date"] = pd.to_datetime(frame["date"], unit="ms", utc=True).dt.normalize()
    return frame.set_index("date").sort_index()


def trailing_percentile(series):
    """Rank against the preceding window, the current bar excluded."""
    values = series.to_numpy(dtype=float)
    out = np.full(len(values), np.nan)
    for i in range(PERCENTILE_MIN, len(values)):
        if np.isnan(values[i]):
            continue
        history = values[max(0, i - PERCENTILE_WINDOW):i]
        history = history[~np.isnan(history)]
        if len(history) < PERCENTILE_MIN:
            continue
        out[i] = np.mean(history <= values[i])
    return pd.Series(out, index=series.index)


def forward_return(price, horizon):
    return price.shift(-horizon) / price - 1


def forward_drawdown(price, horizon):
    values = price.to_numpy(dtype=float)
    out = np.full(len(values), np.nan)
    for i in range(len(values) - horizon):
        window = values[i + 1:i + 1 + horizon]
        if np.isnan(values[i]) or np.isnan(window).any():
            continue
        out[i] = np.min(window) / values[i] - 1
    return pd.Series(out, index=price.index)


def window_of(index, start, end):
    dates = pd.Series(pd.to_datetime(index).strftime("%Y-%m-%d"), index=index)
    mask = dates >= start
    if end is not None:
        mask = mask & (dates <= end)
    return mask


def episodes(flag, start, end):
    flagged = flag.fillna(False).astype(bool)
    starts = flagged & ~flagged.shift(1, fill_value=False)
    return int((starts & window_of(flag.index, start, end)).sum())


def effect(flag, target, start, end):
    mask = window_of(flag.index, start, end) & flag.notna() & target.notna()
    flagged = flag[mask].fillna(False).astype(bool)
    values = target[mask]
    row = {"n": int(len(values)), "flagged": int(flagged.sum())}
    if flagged.sum() >= 3:
        row["effect"] = round(float(values[flagged].mean() - values.mean()), 6)
    return row


def verdict_of(fresh):
    if any("effect" not in row for row in fresh):
        return "insufficient"
    if any(row["episodes"] < EPISODE_BAR for row in fresh):
        return "insufficient"
    signs = [row["effect"] < 0 for row in fresh]
    if signs[0] != signs[1]:
        return "rejected"
    return "kept"


def item_verdict(cells):
    """One word for the item, from the cells, in the order a reader expects.

    A cell that reaches none of its bars is insufficient, not rejected, and
    one insufficient cell means the item is not settled. A sign that flips
    between the two fresh windows is rejected. Kept is only every cell kept.
    """
    verdicts = [cell["verdict"] for cell in cells]
    if any(verdict == "insufficient" for verdict in verdicts):
        return "insufficient"
    if any(verdict == "rejected" for verdict in verdicts):
        return "rejected"
    if verdicts and all(verdict == "kept" for verdict in verdicts):
        return "kept"
    raise ValueError(f"no verdict among {verdicts}")


def lookahead(series):
    rank = trailing_percentile(series.shift(1))
    cut = rank.index[len(rank) // 2]
    perturbed = series.copy()
    perturbed[perturbed.index > cut] = perturbed[perturbed.index > cut] * 1.5 + 3
    after = trailing_percentile(perturbed.shift(1))
    before = rank[rank.index <= cut]
    return bool(np.allclose(before, after.reindex(before.index), equal_nan=True))


def main():
    commit = prereg_commit()
    panel = pd.read_csv(PANEL, index_col=0, parse_dates=True)
    panel.index = pd.to_datetime(panel.index, utc=True).normalize()
    cells = []
    passed = {}
    for asset in ASSETS:
        skew = market(f"skew_25d_{asset}_")["30"].astype(float)
        dvol = market(f"dvol_{asset}_")["dvol"].astype(float)
        price = panel[f"{asset.lower()}_price"].astype(float)
        skew_rank = trailing_percentile(skew.shift(1))
        dvol_rank = trailing_percentile(dvol.shift(1))
        flag = (skew_rank.ge(SKEW_CUT) & dvol_rank.le(DVOL_CUT)).where(
            skew_rank.notna() & dvol_rank.notna())
        passed[asset] = lookahead(skew) and lookahead(dvol)
        for horizon in HORIZONS:
            target = forward_return(price, horizon)
            fresh = []
            for name, start, end in FRESH:
                row = effect(flag, target, start, end)
                row["episodes"] = episodes(flag, start, end)
                row["window"] = name
                fresh.append(row)
            reported = effect(flag, target, REPORTED[1], REPORTED[2])
            reported["episodes"] = episodes(flag, REPORTED[1], REPORTED[2])
            cells.append({
                "asset": asset, "target": "return", "horizon": horizon,
                "fresh": fresh, "reported_2020_2025": reported,
                "verdict": verdict_of(fresh),
            })
        for window in WINDOWS:
            target = forward_drawdown(price, window)
            fresh = []
            for name, start, end in FRESH:
                row = effect(flag, target, start, end)
                row["episodes"] = episodes(flag, start, end)
                row["window"] = name
                fresh.append(row)
            reported = effect(flag, target, REPORTED[1], REPORTED[2])
            reported["episodes"] = episodes(flag, REPORTED[1], REPORTED[2])
            cells.append({
                "asset": asset, "target": "drawdown", "horizon": window,
                "fresh": fresh, "reported_2020_2025": reported,
                "verdict": verdict_of(fresh),
            })
    payload = {
        "prereg_commit": commit,
        "lookahead_passed": passed,
        "cells": cells,
        "verdict": item_verdict(cells),
    }
    path = write_result("q2_skew_no_vol", payload,
                        inputs=["data/laevitas/market", "data/panel.csv", PREREG])
    print(json.dumps({"path": path, "lookahead": passed,
                      "verdicts": [cell["verdict"] for cell in cells]}))


if __name__ == "__main__":
    main()
