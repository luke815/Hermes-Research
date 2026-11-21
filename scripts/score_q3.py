"""Score the pre-registered Q3 cells for BTC and ETH.

The rules are research/outside/PREREG_Q3.md, committed before this script
existed. Laevitas serves per-coin implied vol for BTC and ETH only, so the
broader universe the backlog names is not scored.
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
from regime_tester.periods import PERIODS  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREREG = "research/outside/PREREG_Q3.md"
MARKET = os.path.join(ROOT, "data", "laevitas", "market")
PANEL = os.path.join(ROOT, "data", "panel.csv")
CUT = 0.1
HORIZONS = (10, 20)
WINDOWS = (10, 20)
EPISODE_BAR = 20
PERCENTILE_WINDOW = 365
PERCENTILE_MIN = 252
ASSETS = ("BTC", "ETH")
REPORTED = ("2020-2025", "2020-01-01", "2025-12-31")


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
    mask = pd.Series(True, index=index)
    if start is not None:
        mask = mask & (dates >= start)
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


def verdict_of(periods, counts):
    """The pre-registered bar, applied to validation and test.

    Fewer than 20 episodes across train and validation is insufficient. A
    missing effect is insufficient. A sign that flips between validation and
    test is rejected.
    """
    held = [periods.get(name, {}) for name in ("validation", "test")]
    if any("effect" not in row for row in held):
        return "insufficient"
    if counts["train"] + counts["validation"] < EPISODE_BAR:
        return "insufficient"
    signs = [row["effect"] < 0 for row in held]
    if signs[0] != signs[1]:
        return "rejected"
    return "kept"


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
        frame = market(f"iv_rv_{asset}_")
        ratio = (frame["iv_30"] / frame["rv_30"]).astype(float)
        price = panel[f"{asset.lower()}_price"].astype(float)
        rank = trailing_percentile(ratio.shift(1))
        flag = rank.le(CUT).where(rank.notna())
        passed[asset] = lookahead(ratio)
        for target_name, horizons, builder in (
            ("return", HORIZONS, forward_return),
            ("drawdown", WINDOWS, forward_drawdown),
        ):
            for horizon in horizons:
                target = builder(price, horizon).reindex(flag.index)
                periods = {}
                counts = {}
                for name, start, end in PERIODS:
                    row = effect(flag, target, start, end)
                    row["episodes"] = episodes(flag, start, end)
                    periods[name] = row
                    counts[name] = row["episodes"]
                reported = effect(flag, target, REPORTED[1], REPORTED[2])
                reported["episodes"] = episodes(flag, REPORTED[1], REPORTED[2])
                cells.append({
                    "asset": asset, "target": target_name, "horizon": horizon,
                    "periods": periods, "reported_2020_2025": reported,
                    "verdict": verdict_of(periods, counts),
                })
    payload = {
        "prereg_commit": commit,
        "lookahead_passed": passed,
        "broader_universe": "not served: per-coin IV exists for BTC and ETH only",
        "cells": cells,
    }
    path = write_result("q3_ivrv", payload,
                        inputs=["data/laevitas/market", "data/panel.csv", PREREG])
    print(json.dumps({"path": path, "lookahead": passed,
                      "verdicts": [cell["verdict"] for cell in cells]}))


if __name__ == "__main__":
    main()
