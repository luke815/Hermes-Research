"""Score the pre-registered A7(2), A7(3) and A7(4) cells.

The rules are research/outside/PREREG_A7.md, committed before this script
existed. The script reads that commit and refuses to score when it is not an
ancestor of HEAD, so a rule edited in the scoring commit is not
pre-registered.

A7(1) is not scored here. Its panel has a bad close and a research run does
not rewrite it. A7(2)'s filter on A7(1) is left for the run that rescores it.
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
from regime_tester.cycle_score import candidate_mask  # noqa: E402
from regime_tester.episodes import top_event  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREREG = "research/outside/PREREG_A7.md"
TRAIN_END = "2024-06-30"
VAL_START, VAL_END = "2024-07-01", "2025-12-31"
TEST_START = "2026-01-01"
T_BAR = 2.0
N_BAR = 40
COST_BPS = 15
TOP_CUT = 0.8
BOTTOM_CUT = 0.2
PERCENTILE_WINDOW = 365
PERCENTILE_MIN = 252
ALT_NAMES = ("ADA", "SOL", "LINK", "XRP", "AVAX")
POOLED_MIN = 3

FEATURES = (
    ("skew", "skew_25d", "30"),
    ("risk_reversal", "risk_reversal_25d", "30"),
    ("iv_minus_rv", "iv_rv", None),
    ("basis", "oi_weighted_basis", "30"),
    ("oi_change", "derivs_summary", None),
)
NEIGHBOUR_TENORS = ("7", "90")


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


def market(prefix):
    """Every window of one series, one row per date, the last one kept."""
    store = os.path.join(ROOT, "data", "laevitas", "market")
    rows = []
    for name in sorted(os.listdir(store)):
        if name.startswith(prefix):
            rows.extend(json.load(open(os.path.join(store, name))).get("items", []))
    frame = pd.DataFrame(rows).drop_duplicates("date", keep="last")
    frame["date"] = pd.to_datetime(frame["date"], unit="ms", utc=True).dt.normalize()
    return frame.set_index("date").sort_index()


def trailing_percentile(series):
    """Share of the previous 365 bars at or below the current bar.

    The current bar is excluded, and a window shorter than 252 bars is empty.
    """
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


def period_of(index):
    dates = pd.Series(pd.to_datetime(index).strftime("%Y-%m-%d"), index=index)
    out = pd.Series("train", index=index)
    out[(dates >= VAL_START) & (dates <= VAL_END)] = "validation"
    out[dates >= TEST_START] = "test"
    return out


def forward_return(price, horizon):
    """Return from today's close to the close `horizon` bars later."""
    return price.shift(-horizon) / price - 1


def carry(funding, horizon):
    """Sum of the next `horizon` funding prints. A missing day leaves it empty."""
    values = funding.to_numpy(dtype=float)
    out = np.full(len(values), np.nan)
    for i in range(len(values) - horizon):
        window = values[i:i + horizon]
        if np.isnan(window).any():
            continue
        out[i] = window.sum()
    return pd.Series(out, index=funding.index)


def net_target(price, funding, horizon):
    """Forward return minus the round trip and the funding carry."""
    gross = forward_return(price, horizon)
    cost = 2 * COST_BPS / 10_000
    held = carry(funding, horizon)
    return gross - cost - held


def spread_stats(flag, target, horizon):
    """Flagged mean minus unflagged mean, overlapping and non-overlapping."""
    which = period_of(flag.index)
    out = {}
    for name in ("train", "validation", "test"):
        mask = (which == name) & flag.notna() & target.notna()
        flagged = flag[mask].fillna(False).astype(bool)
        values = target[mask]
        row = {"n": int(len(values)), "flagged": int(flagged.sum())}
        if len(values) and flagged.sum() and (~flagged).sum():
            row["spread"] = _round(values[flagged].mean() - values[~flagged].mean())
            row["hit_rate"] = _round(float((values[flagged] > 0).mean()))
            row["base_rate"] = _round(float((values > 0).mean()))
            step = values.iloc[::horizon]
            flagged_step = flagged.iloc[::horizon]
            row["independent"] = int(np.ceil(len(values) / horizon))
            row["flagged_independent"] = int(flagged_step.sum())
            if flagged_step.sum() >= 2 and (~flagged_step).sum() >= 2:
                diff = step[flagged_step].mean() - step[~flagged_step].mean()
                pooled = np.sqrt(
                    step[flagged_step].var(ddof=1) / flagged_step.sum()
                    + step[~flagged_step].var(ddof=1) / (~flagged_step).sum())
                row["spread_independent"] = _round(diff)
                if pooled and not np.isnan(pooled):
                    row["t_independent"] = _round(diff / pooled)
        out[name] = row
    return out


def verdict_of(stats):
    """Sign held in both held-out periods, t at least 2, n at least 40."""
    held = [stats.get(name, {}) for name in ("validation", "test")]
    if any("spread_independent" not in row for row in held):
        return "insufficient"
    signs = [row["spread_independent"] > 0 for row in held]
    if signs[0] != signs[1]:
        return "rejected"
    counts = [row.get("flagged_independent", 0) for row in held]
    if any(count < N_BAR for count in counts):
        return "insufficient"
    t_stats = [row.get("t_independent") for row in held]
    if any(t is None or abs(t) < T_BAR for t in t_stats):
        return "insufficient"
    return "kept"


def _round(value):
    if value is None or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
        return None
    return round(float(value), 6)


def feature_series(asset, kind, tenor):
    """One daily series for an asset, from the market store."""
    upper = asset.upper()
    if kind == "skew_25d" or kind == "risk_reversal_25d" or kind == "oi_weighted_basis":
        frame = market(f"{kind}_{upper}_")
        return frame[tenor].astype(float)
    if kind == "iv_rv":
        frame = market(f"iv_rv_{upper}_")
        return (frame["iv_30"] - frame["rv_30"]).astype(float)
    if kind == "derivs_summary":
        frame = market(f"derivs_summary_{upper}_")
        return frame["open_interest"].astype(float).pct_change(7)
    raise ValueError(kind)


def score_derivatives(panel):
    """A7(2): each feature, both tails, both horizons, both assets."""
    cells = []
    for asset in ("btc", "eth"):
        price = panel[f"{asset}_price"].astype(float)
        funding = panel[f"{asset}_funding"].astype(float)
        for name, kind, tenor in FEATURES:
            level = feature_series(asset, kind, tenor)
            change = level.diff(5) if name != "oi_change" else level
            series = {"percentile": trailing_percentile(level.shift(1)),
                      "change_5": trailing_percentile(change.shift(1))}
            for transform, rank in series.items():
                aligned = rank.reindex(price.index)
                for side, cut in (("top", TOP_CUT), ("bottom", BOTTOM_CUT)):
                    flag = aligned.ge(cut) if side == "top" else aligned.le(cut)
                    flag = flag.where(aligned.notna())
                    for horizon in (1, 3):
                        target = net_target(price, funding, horizon)
                        stats = spread_stats(flag, target, horizon)
                        cells.append({
                            "feature": name,
                            "transform": transform,
                            "side": side,
                            "asset": asset,
                            "horizon": horizon,
                            "verdict": verdict_of(stats),
                            "periods": stats,
                        })
        for tenor in NEIGHBOUR_TENORS:
            for kind in ("skew_25d", "risk_reversal_25d", "oi_weighted_basis"):
                level = feature_series(asset, kind, tenor)
                rank = trailing_percentile(level.shift(1)).reindex(price.index)
                flag = rank.ge(TOP_CUT).where(rank.notna())
                target = net_target(price, funding, 1)
                cells.append({
                    "feature": kind,
                    "tenor": tenor,
                    "side": "top",
                    "asset": asset,
                    "horizon": 1,
                    "neighbour": True,
                    "verdict": "neighbour",
                    "periods": spread_stats(flag, target, 1),
                })
    return cells


def score_crowding():
    """A7(3): OI stretched against volume, and 30-day OI change, before alt tops."""
    panel = pd.read_csv(os.path.join(ROOT, "data", "panel.csv"), index_col=0)
    panel.index = pd.to_datetime(panel.index, utc=True)
    basket = panel["alt_price"].astype(float)
    label = top_event(basket, 30, 0.20).where(candidate_mask(basket, "top"))
    per_name = {}
    flags = {}
    for name in ALT_NAMES:
        summary = market(f"derivs_summary_{name}_")
        oi = summary["open_interest"].astype(float)
        volume = summary["volume"].astype(float)
        ratio = (oi / volume.replace(0, np.nan)).reindex(basket.index)
        change = oi.pct_change(30).reindex(basket.index)
        for feature, series in (("oi_over_volume", ratio), ("oi_change_30d", change)):
            rank = trailing_percentile(series.shift(1))
            flag = rank.ge(0.9).where(rank.notna())
            flags[(name, feature)] = flag
            per_name[f"{name}_{feature}"] = {
                "flagged_days": int(flag.fillna(False).sum()),
                "lift": lift(flag, label),
            }
    pooled = {}
    for feature in ("oi_over_volume", "oi_change_30d"):
        stacked = pd.concat(
            [flags[(name, feature)].astype(float) for name in ALT_NAMES], axis=1)
        count = stacked.sum(axis=1)
        flag = (count >= POOLED_MIN).where(stacked.notna().any(axis=1))
        target = forward_return(basket, 10) - 2 * COST_BPS / 10_000
        stats = spread_stats(flag, target, 10)
        pooled[feature] = {
            "verdict": verdict_of(stats),
            "lift": lift(flag, label),
            "periods": stats,
        }
    return {"per_name": per_name, "pooled": pooled,
            "survivor_biased": True}


def lift(flag, label):
    """Share of flagged candidate days that top, over the base rate."""
    decided = label.notna()
    flagged = flag.fillna(False).astype(bool) & decided
    base = label[decided].astype(bool)
    if not flagged.sum() or not decided.sum():
        return None
    rate = float(label[flagged].astype(bool).mean())
    base_rate = float(base.mean())
    return {"flagged": int(flagged.sum()), "rate": _round(rate),
            "base_rate": _round(base_rate),
            "lift": _round(rate / base_rate) if base_rate else None}


def score_funding(panel):
    """A7(4): long the cheaper funding, short the dearer, two names only."""
    btc = panel["btc_funding"].astype(float)
    eth = panel["eth_funding"].astype(float)
    btc_price = panel["btc_price"].astype(float)
    eth_price = panel["eth_price"].astype(float)
    signal = -(btc - eth).shift(1)
    cells = []
    for horizon in (1, 3):
        btc_net = net_target(btc_price, btc, horizon)
        eth_net = net_target(eth_price, eth, horizon)
        long_btc = signal > 0
        spread = pd.Series(np.where(long_btc, btc_net - eth_net, eth_net - btc_net),
                           index=panel.index)
        spread = spread.where(signal.notna() & btc_net.notna() & eth_net.notna())
        btc_forward = forward_return(btc_price, horizon)
        excess = spread - btc_forward.where(btc_forward.notna())
        stats = one_sided(excess, horizon)
        cells.append({"horizon": horizon, "verdict": verdict_of(stats),
                      "periods": stats, "names": 2})
    return cells


def one_sided(spread, horizon):
    """Mean of one spread, against zero, non-overlapping."""
    which = period_of(spread.index)
    out = {}
    for name in ("train", "validation", "test"):
        values = spread[(which == name) & spread.notna()]
        row = {"n": int(len(values)), "flagged": int(len(values))}
        if len(values):
            row["spread"] = _round(values.mean())
            row["hit_rate"] = _round(float((values > 0).mean()))
            step = values.iloc[::horizon]
            row["independent"] = int(len(step))
            row["flagged_independent"] = int(len(step))
            row["spread_independent"] = _round(step.mean())
            if len(step) >= 2 and step.std(ddof=1):
                row["t_independent"] = _round(
                    step.mean() / (step.std(ddof=1) / np.sqrt(len(step))))
        out[name] = row
    return out


def lookahead_check(panel):
    """Perturbing prices after day t leaves the features at t unchanged."""
    asset = "btc"
    level = feature_series(asset, "skew_25d", "30")
    rank = trailing_percentile(level.shift(1))
    cut = rank.index[len(rank) // 2]
    perturbed = level.copy()
    perturbed[perturbed.index > cut] = perturbed[perturbed.index > cut] * 1.5 + 7
    rank_after = trailing_percentile(perturbed.shift(1))
    before = rank[rank.index <= cut]
    after = rank_after.reindex(before.index)
    return bool(np.allclose(before.to_numpy(dtype=float),
                            after.to_numpy(dtype=float), equal_nan=True))


def main():
    commit = prereg_commit()
    panel = pd.read_csv(os.path.join(ROOT, "data", "panel.csv"), index_col=0)
    panel.index = pd.to_datetime(panel.index, utc=True)
    derivatives = score_derivatives(panel)
    crowding = score_crowding()
    funding = score_funding(panel)
    payload = {
        "prereg_commit": commit,
        "a7_1": "blocked on a bad close in data/panel_xs_laevitas; not scored",
        "lookahead_passed": lookahead_check(panel),
        "a7_2": derivatives,
        "a7_3": crowding,
        "a7_4": funding,
    }
    path = write_result(
        "a7_rest", payload,
        inputs=["data/panel.csv", "data/laevitas/market", PREREG])
    kept = [c for c in derivatives if c["verdict"] == "kept"]
    print(json.dumps({
        "path": path,
        "lookahead_passed": payload["lookahead_passed"],
        "a7_2_cells": len(derivatives),
        "a7_2_kept": len(kept),
        "a7_3": {k: v["verdict"] for k, v in crowding["pooled"].items()},
        "a7_4": [c["verdict"] for c in funding],
    }))


if __name__ == "__main__":
    main()
