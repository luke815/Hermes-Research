"""Score the PREREG4 cells and write the results file.

The rules are research/outside/PREREG4.md, committed before this script
existed. The script reads that commit and refuses to score when it is not an
ancestor of HEAD, so a rule edited in the scoring commit is not pre-registered.

Coin open interest is the market-level open interest divided by the price,
from data/laevitas/market/derivs_summary. The per-instrument coin field starts
in 2024, which would leave train empty. DVOL comes from data/laevitas/market/dvol.
Funding and price come from data/panel.csv.

Every feature is shifted so bar t uses only bars before t. An event counted
inside a forward window is counted from bars after t, which is the target,
not the signal.
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
PREREG = "research/outside/PREREG4.md"
TRAIN_END = "2024-06-30"
VAL_START, VAL_END = "2024-07-01", "2025-12-31"
TEST_START = "2026-01-01"
T_BAR = 2.5
EPISODE_BAR = 30
INDEPENDENT_BAR = 40
A6_EPISODE_BAR = 15
COST_BPS = 15


def prereg_commit():
    """The commit that added the pre-registration. It must precede HEAD."""
    added = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=%H", "--", PREREG],
        cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    if len(added) != 1:
        raise SystemExit(f"pre-registration was added in {len(added)} commits")
    commit = added[0]
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=ROOT)
    if ancestor.returncode != 0:
        raise SystemExit("pre-registration commit is not an ancestor of HEAD")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
        check=True).stdout.strip()
    if head == commit:
        raise SystemExit("scoring in the same commit as the pre-registration")
    return commit


def load_frames():
    """One daily frame per asset, indexed by date string."""
    panel = pd.read_csv(os.path.join(ROOT, "data", "panel.csv"), index_col=0)
    frames = {}
    for asset in ("btc", "eth"):
        upper = asset.upper()
        summary = _market(f"derivs_summary_{upper}_")
        coin = summary["open_interest"] / summary["price"].replace(0, np.nan)
        dvol = _market(f"dvol_{upper}_")["dvol"]
        frame = pd.DataFrame({
            "price": panel[f"{asset}_price"],
            "funding": panel[f"{asset}_funding"],
        })
        frame.index = pd.to_datetime(frame.index).strftime("%Y-%m-%d")
        frame["coin_oi"] = _by_date(coin)
        frame["dvol"] = _by_date(dvol)
        frames[asset] = frame.sort_index()
    return frames


def _market(prefix):
    store = os.path.join(ROOT, "data", "laevitas", "market")
    rows = []
    for name in sorted(os.listdir(store)):
        if name.startswith(prefix):
            rows.extend(json.load(open(os.path.join(store, name))).get("items", []))
    frame = pd.DataFrame(rows).drop_duplicates("date")
    frame["date"] = pd.to_datetime(frame["date"], unit="ms", utc=True)
    return frame.set_index("date").sort_index()


def _by_date(series):
    dated = series.copy()
    dated.index = pd.to_datetime(dated.index).strftime("%Y-%m-%d")
    return dated.groupby(level=0).last()


def period_of(dates):
    """Train, validation or test. A cluster takes the period of its first bar."""
    out = pd.Series("train", index=dates)
    out[(dates >= VAL_START) & (dates <= VAL_END)] = "validation"
    out[dates >= TEST_START] = "test"
    return out


def cluster_count(flag):
    """Runs of consecutive flagged days. The count is the episode count."""
    flagged = flag.fillna(False).astype(bool)
    starts = flagged & ~flagged.shift(1, fill_value=False)
    which = period_of(flagged.index)
    return {
        "total": int(starts.sum()),
        "train": int((starts & (which == "train")).sum()),
        "validation": int((starts & (which == "validation")).sum()),
        "test": int((starts & (which == "test")).sum()),
    }


def trailing_percentile(series, window, minimum):
    """Share of the previous `window` bars at or below the current bar.

    The current bar is excluded, and a window shorter than `minimum` is empty.
    """
    values = series.to_numpy(dtype=float)
    out = np.full(len(values), np.nan)
    for i in range(len(values)):
        if np.isnan(values[i]):
            continue
        history = values[max(0, i - window):i]
        history = history[~np.isnan(history)]
        if len(history) < minimum:
            continue
        out[i] = np.mean(history <= values[i])
    return pd.Series(out, index=series.index)


def forward_return(price, horizon):
    """Return from today's close to the close `horizon` bars later, net of costs."""
    gross = price.shift(-horizon) / price - 1
    return gross - 2 * COST_BPS / 10_000


def forward_drawdown(price, horizon):
    """Worst close-to-close loss over the next `horizon` bars."""
    values = price.to_numpy(dtype=float)
    out = np.full(len(values), np.nan)
    for i in range(len(values) - horizon):
        if np.isnan(values[i]):
            continue
        window = values[i + 1:i + 1 + horizon]
        if np.isnan(window).any():
            continue
        out[i] = np.min(window / values[i] - 1)
    return pd.Series(out, index=price.index)


def event_within(event, horizon):
    """True when the event is true on any of the next `horizon` bars."""
    coming = event.fillna(False).astype(bool)
    out = pd.Series(False, index=coming.index)
    for step in range(1, horizon + 1):
        out = out | coming.shift(-step).fillna(False)
    return out


def hazard(state, event, horizon):
    """Share of state days followed by the event, minus the share outside it."""
    followed = event_within(event, horizon)
    which = period_of(state.index)
    out = {}
    for name in ("train", "validation", "test"):
        mask = (which == name) & state.notna()
        inside = state[mask].fillna(False).astype(bool)
        happened = followed[mask]
        if inside.sum() == 0 or (~inside).sum() == 0:
            out[name] = {"state_days": int(inside.sum())}
            continue
        state_share = float(happened[inside].mean())
        base_share = float(happened[~inside].mean())
        out[name] = {
            "state_days": int(inside.sum()),
            "state_share": round(state_share, 4),
            "base_share": round(base_share, 4),
            "lift": round(state_share - base_share, 4),
        }
    return out


def spread(flag, target, horizon):
    """Flagged mean minus unflagged mean, with the non-overlapping t-stat."""
    which = period_of(flag.index)
    out = {}
    for name in ("train", "validation", "test"):
        mask = (which == name) & flag.notna() & target.notna()
        flagged = flag[mask].fillna(False).astype(bool)
        values = target[mask]
        if not len(values) or flagged.sum() == 0 or (~flagged).sum() == 0:
            out[name] = {"n": int(len(values)), "flagged": int(flagged.sum())}
            continue
        step = values.iloc[::horizon]
        flagged_step = flagged.iloc[::horizon]
        both = flagged_step.sum() >= 2 and (~flagged_step).sum() >= 2
        diff = None
        t_stat = None
        if both:
            diff = step[flagged_step].mean() - step[~flagged_step].mean()
            pooled = np.sqrt(
                step[flagged_step].var(ddof=1) / flagged_step.sum()
                + step[~flagged_step].var(ddof=1) / (~flagged_step).sum())
            if pooled and not np.isnan(pooled):
                t_stat = diff / pooled
        out[name] = {
            "n": int(len(values)),
            "flagged": int(flagged.sum()),
            "independent": int(np.ceil(len(values) / horizon)),
            "spread": _round(values[flagged].mean() - values[~flagged].mean()),
            "spread_independent": _round(diff),
            "t_independent": _round(t_stat),
        }
    return out


def _round(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    return round(float(value), 6)


def return_verdict(summary, episodes):
    """Insufficient below the bar, rejected on a sign flip, else recorded."""
    train_val = episodes["train"] + episodes["validation"]
    if train_val < EPISODE_BAR:
        return "insufficient"
    val = summary["validation"].get("spread_independent")
    test = summary["test"].get("spread_independent")
    if val is None or test is None or np.sign(val) != np.sign(test):
        return "rejected" if val is not None and test is not None else "insufficient"
    if (summary["validation"].get("independent") or 0) < INDEPENDENT_BAR:
        return "insufficient"
    if abs(summary["validation"].get("t_independent") or 0) < T_BAR:
        return "insufficient"
    return "recorded"


def score_a1(frame):
    """Crowded funding followed by a de-leveraging event, against a vol control."""
    funding_pct = trailing_percentile(frame["funding"], 365, 180)
    crowded = (funding_pct >= 0.8).shift(1)
    coin_drop = frame["coin_oi"].pct_change(3) <= -0.10
    dvol_pct = trailing_percentile(frame["dvol"].diff(5), 365, 180)
    dvol_spike = dvol_pct >= 0.9
    funding_reset = funding_pct < 0.5
    vol = frame["price"].pct_change().rolling(20).std().shift(1)
    out = {"episodes": cluster_count(crowded)}
    for horizon in (10, 20):
        for name, event in (("coin_drop", coin_drop), ("dvol_spike", dvol_spike),
                            ("funding_reset", funding_reset)):
            out[f"{name}_h{horizon}"] = hazard(crowded, event, horizon)
    out["vol_control"] = _vol_control(vol, crowded, coin_drop)
    out["verdict"] = _hazard_verdict(out)
    return out


def _vol_control(vol, crowded, event):
    """The coin-drop lift inside each quintile of trailing realized vol."""
    quintile = pd.Series(np.nan, index=vol.index)
    history = vol.expanding(min_periods=180)
    for i, (date, value) in enumerate(vol.items()):
        if np.isnan(value) or i < 180:
            continue
        past = vol.iloc[:i].dropna()
        quintile.loc[date] = float((past <= value).mean())
    bands = pd.cut(quintile, [0, 0.2, 0.4, 0.6, 0.8, 1.0],
                   labels=["q1", "q2", "q3", "q4", "q5"])
    out = {}
    for band in ("q1", "q2", "q3", "q4", "q5"):
        inside = crowded.where(bands == band)
        out[band] = hazard(inside, event, 10)
    return out


def _hazard_verdict(block):
    """Recorded only if the lift keeps its sign, and the vol control does too.

    The pre-registration passes the crowded state only when its lift over the
    unconditional hazard keeps its sign inside the vol quintile it falls in.
    A lift that vanishes inside every quintile is the vol control, not a
    finding, so the cell is insufficient.
    """
    for key, value in block.items():
        if not key.startswith("coin_drop"):
            continue
        val = value.get("validation", {}).get("lift")
        test = value.get("test", {}).get("lift")
        if val is None or test is None or np.sign(val) != np.sign(test) or not np.sign(val):
            return "rejected" if val is not None and test is not None else "insufficient"
    held = []
    for band, value in block.get("vol_control", {}).items():
        val = value.get("validation", {}).get("lift")
        test = value.get("test", {}).get("lift")
        if val is None or test is None:
            continue
        held.append(np.sign(val) == np.sign(test) and np.sign(val) != 0)
    # One quintile agreeing is the one the search found, and one asset agreeing
    # is the asset the search found. The caller joins the two assets.
    if len(held) < 2 or not all(held):
        return "insufficient"
    return "recorded_pending_other_asset"


def score_a2(frame):
    """Four quadrants of 7-day price return and 7-day coin-OI change."""
    ret7 = frame["price"].pct_change(7).shift(1)
    coin7 = frame["coin_oi"].pct_change(7).shift(1)
    out = {}
    for horizon in (10, 20):
        target = forward_return(frame["price"], horizon)
        control = _price_only(ret7, target, horizon)
        for price_up in (True, False):
            for oi_up in (True, False):
                flag = (ret7 > 0) if price_up else (ret7 <= 0)
                flag = flag & ((coin7 > 0) if oi_up else (coin7 <= 0))
                name = ("up" if price_up else "down") + "_" + (
                    "building" if oi_up else "leaving")
                summary = spread(flag, target, horizon)
                out[f"{name}_h{horizon}"] = {
                    "episodes": cluster_count(flag),
                    "summary": summary,
                    "control": control["up" if price_up else "down"],
                    "verdict": return_verdict(summary, cluster_count(flag)),
                }
    return out


def _price_only(ret7, target, horizon):
    """The 7-day price return alone, the control a quadrant has to beat."""
    return {
        "up": spread(ret7 > 0, target, horizon),
        "down": spread(ret7 <= 0, target, horizon),
    }


def score_a3(frame):
    """Crowded funding split by coin open interest building or leaving."""
    funding_pct = trailing_percentile(frame["funding"], 365, 180)
    crowded = (funding_pct >= 0.8).shift(1)
    coin7 = frame["coin_oi"].pct_change(7).shift(1)
    usd7 = (frame["coin_oi"] * frame["price"]).pct_change(7).shift(1)
    out = {}
    for horizon in (10, 20):
        target = forward_return(frame["price"], horizon)
        for building in (True, False):
            coin_flag = crowded & ((coin7 > 0) if building else (coin7 <= 0))
            usd_flag = crowded & ((usd7 > 0) if building else (usd7 <= 0))
            name = "building" if building else "leaving"
            summary = spread(coin_flag, target, horizon)
            out[f"{name}_h{horizon}"] = {
                "episodes": cluster_count(coin_flag),
                "summary": summary,
                "usd_control": spread(usd_flag, target, horizon),
                "verdict": return_verdict(summary, cluster_count(coin_flag)),
            }
    return out


def score_a5(frame):
    """The 7-day funding-state transition matrix. A base rate, so no verdict."""
    funding_pct = trailing_percentile(frame["funding"], 365, 180).shift(1)
    default = frame["funding"] == 0.01
    state = pd.Series("neutral", index=frame.index)
    state[funding_pct >= 0.8] = "crowded"
    state[(funding_pct <= 0.2) & ~default.shift(1).fillna(False)] = "washed"
    which = period_of(frame.index)
    future = state.shift(-7)
    out = {}
    for name in ("train", "validation", "test"):
        counts = {}
        for origin in ("crowded", "neutral", "washed"):
            days = (which == name) & (state == origin)
            if not days.any():
                counts[origin] = {"n": 0}
                continue
            landed = future[days].value_counts(normalize=True)
            counts[origin] = {
                "n": int(days.sum()),
                "to": {key: round(float(value), 4) for key, value in landed.items()},
            }
        out[name] = counts
    return {"matrix": out, "verdict": None}


def score_a6(frame):
    """A funding reset while price holds, against a reset with a drop."""
    funding_pct = trailing_percentile(frame["funding"], 365, 180)
    was_crowded = (funding_pct >= 0.8).shift(5)
    reset = was_crowded & (funding_pct.shift(1) < 0.5)
    held = frame["price"].pct_change(5).shift(1) >= 0
    out = {}
    for horizon in (10, 20):
        target = forward_return(frame["price"], horizon)
        drawdown = forward_drawdown(frame["price"], horizon)
        for name, flag in (("holds", reset & held), ("flush", reset & ~held.fillna(False))):
            summary = spread(flag, target, horizon)
            episodes = cluster_count(flag)
            out[f"{name}_h{horizon}"] = {
                "episodes": episodes,
                "summary": summary,
                "drawdown": spread(flag, drawdown, horizon),
                "verdict": _a6_verdict(summary, episodes),
            }
    return out


def _a6_verdict(summary, episodes):
    train_val = episodes["train"] + episodes["validation"]
    if train_val < A6_EPISODE_BAR:
        return "insufficient"
    val = summary["validation"].get("spread_independent")
    test = summary["test"].get("spread_independent")
    if val is None or test is None:
        return "insufficient"
    if np.sign(val) != np.sign(test):
        return "rejected"
    return "recorded"


def main():
    commit = prereg_commit()
    frames = load_frames()
    cells = {}
    for asset, frame in frames.items():
        cells[f"A1_{asset}"] = score_a1(frame)
        cells[f"A2_{asset}"] = score_a2(frame)
        cells[f"A3_{asset}"] = score_a3(frame)
        cells[f"A5_{asset}"] = score_a5(frame)
        cells[f"A6_{asset}"] = score_a6(frame)
    for asset in ("btc", "eth"):
        other = "eth" if asset == "btc" else "btc"
        if cells[f"A1_{asset}"]["verdict"] == "recorded_pending_other_asset":
            cells[f"A1_{asset}"]["verdict"] = (
                "recorded" if cells[f"A1_{other}"]["verdict"]
                == "recorded_pending_other_asset" else "insufficient")
    payload = {"item": "P4", "prereg": PREREG, "prereg_commit": commit,
               "cells": cells}
    path = write_result("p4_cells", payload, inputs=[
        "data/panel.csv", "data/laevitas/market", PREREG])
    print(path)


if __name__ == "__main__":
    main()
