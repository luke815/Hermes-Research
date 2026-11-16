"""Cross-sectional funding and open-interest test.

Pre-registered 2026-11-16T04:01:52Z in research/log.md. Reads data/panel_xs,
which is already on disk, and scores only the two signals named there.
No pull, no confirmation.

The funding signal at date t is the mean of the 7 funding closes ending
yesterday. The open-interest signal is the percent change over the same
window. The target is the forward return starting at today's close.
Perturbing every value after t cannot move the signal at t, and the
lookahead check below asserts that.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from regime_tester.costs import round_trip

ROOT = Path(__file__).resolve().parent.parent
PANEL = ROOT / "data" / "panel_xs"
UNIVERSE = ROOT / "data" / "universe.csv"
OUT = ROOT / "results" / "2026-11-16_xs_funding_oi.json"

WINDOWS = (7, 3, 14)
HORIZONS = (1, 3, 10)
PRIMARY = 7
MIN_NAMES = 20
# The panel has no USD open interest on the live names, so every name takes
# the thin tier. The 29 stopped names that do have oi_usd are delisted, and
# using their last open interest to pick a cheaper tier would be a look ahead.
ROUND_TRIP = round_trip(None)

PERIODS = (
    ("train", None, "2024-06-30"),
    ("validation", "2024-07-01", "2025-12-31"),
    ("test", "2026-01-01", None),
)


def base_of(symbol):
    """Strip the quote and the venue suffix so the same coin collapses."""
    stem = symbol.split(".")[0]
    for suffix in ("_PERP", "USDT", "USDC", "USD"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return stem


def load_series():
    """Close, funding and open interest per base, longest history wins.

    A name is present on a date only when its file has a value that date.
    Funding and open interest are never filled forward and never set to zero.
    """
    non_crypto = set()
    if UNIVERSE.exists():
        universe = pd.read_csv(UNIVERSE)
        if "non_crypto" in universe.columns:
            flagged = universe[universe["non_crypto"].fillna("").astype(str).str.strip() != ""]
            non_crypto = set(flagged["symbol"])
    candidates = {}
    for path in sorted(PANEL.glob("*.csv")):
        symbol = path.stem.split("_", 1)[1]
        if symbol in non_crypto:
            continue
        header = path.read_text(encoding="utf-8").split("\n", 1)[0].split(",")
        wanted = [c for c in ("date", "close", "funding_rate", "oi_usd") if c in header]
        if "close" not in wanted:
            continue
        if "funding_rate" not in wanted and "oi_usd" not in wanted:
            continue
        frame = pd.read_csv(path, usecols=wanted)
        frame = frame.dropna(subset=["close"])
        if frame.empty:
            continue
        frame["date"] = pd.to_datetime(frame["date"], utc=True).dt.normalize()
        frame = frame.drop_duplicates("date").set_index("date").sort_index()
        frame["close"] = frame["close"].astype(float)
        frame = frame[frame["close"] > 0]
        key = base_of(symbol)
        prior = candidates.get(key)
        if prior is None or len(frame) > len(prior[1]):
            candidates[key] = (symbol, frame)
    if "BTC" not in candidates:
        raise SystemExit("BTC is not in the panel")
    btc = candidates["BTC"][1]["close"]
    return btc, candidates


def funding_signal(funding, window):
    """Mean of the last `window` closes, ending yesterday. Missing stays missing."""
    return funding.rolling(window, min_periods=window).mean().shift(1)


def oi_signal(oi, window):
    """Percent change over `window` bars, ending yesterday. Missing stays missing."""
    return (oi.shift(1) / oi.shift(window + 1) - 1)


def forward(close, horizon):
    """Return starting at today's close. Scoring uses this, never the level."""
    return close.shift(-horizon) / close - 1


def build(btc, frames, column, signal_fn, window, horizon):
    """Signal and net forward return, only on dates where the series exists."""
    btc_forward = forward(btc, horizon)
    rows = []
    for name, (_, frame) in frames.items():
        if column not in frame.columns:
            continue
        series = frame[column].astype(float)
        signal = signal_fn(series, window)
        gross = forward(frame["close"], horizon)
        relative = gross - btc_forward.reindex(frame.index)
        out = pd.DataFrame({
            "signal": signal,
            "absolute": gross - ROUND_TRIP,
            "relative": relative - ROUND_TRIP,
        }).dropna(subset=["signal", "absolute"])
        if out.empty:
            continue
        out["name"] = name
        rows.append(out)
    if not rows:
        return pd.DataFrame()
    stacked = pd.concat(rows)
    stacked.index.name = "date"
    return stacked


def daily_stats(stacked):
    """Rank correlation and decile spread per date, names present that date."""
    if stacked.empty:
        return pd.DataFrame()
    rows = []
    for date, group in stacked.groupby(level=0, sort=True):
        if len(group) < MIN_NAMES:
            continue
        signal = group["signal"]
        absolute = group["absolute"]
        relative = group["relative"]
        if signal.nunique() < 2 or absolute.nunique() < 2:
            continue
        ic = float(signal.rank().corr(absolute.rank()))
        ranks = signal.rank(pct=True)
        top = absolute[ranks >= 0.9]
        bottom = absolute[ranks <= 0.1]
        if top.empty or bottom.empty:
            continue
        both = relative.notna()
        ic_rel = float(signal[both].rank().corr(relative[both].rank())) if both.sum() >= MIN_NAMES else None
        rows.append({
            "date": date,
            "names": int(len(group)),
            "ic": ic,
            "spread": float((top.mean() - bottom.mean()) * 100),
            "top_mean": float(top.mean() * 100),
            "bottom_mean": float(bottom.mean() * 100),
            "hit": float((absolute > 0).mean()),
            "ic_rel": ic_rel,
        })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("date")


def t_of_mean(values):
    """t-stat of a mean against zero. Empty or flat returns None, not a claim."""
    values = pd.Series(values).dropna().to_numpy(dtype=float)
    if len(values) < 3 or values.std(ddof=1) == 0:
        return None
    return float(values.mean() / (values.std(ddof=1) / np.sqrt(len(values))))


def period_of(index):
    dates = index.tz_convert("UTC")
    out = pd.Series(pd.NA, index=index, dtype="object")
    for name, start, end in PERIODS:
        mask = pd.Series(True, index=index)
        if start is not None:
            mask &= dates >= pd.Timestamp(start, tz="UTC")
        if end is not None:
            mask &= dates <= pd.Timestamp(end, tz="UTC")
        out[mask] = name
    return out


def summarise(stats, horizon):
    """Non-overlapping summary per period and per year."""
    if stats.empty:
        empty = {"n": 0, "ic_mean": None, "ic_t": None, "spread": None,
                 "spread_t": None, "top_mean": None, "bottom_mean": None,
                 "hit": None, "ic_rel": None}
        return {"n_dates": 0, "names_median": None,
                **{name: empty for name, _, _ in PERIODS}, "by_year": []}
    stride = stats.iloc[::horizon]
    periods = period_of(stride.index)
    out = {"n_dates": int(len(stride)), "names_median": float(stride["names"].median())}
    for name, _, _ in PERIODS:
        part = stride[periods == name]
        out[name] = {
            "n": int(len(part)),
            "ic_mean": float(part["ic"].mean()) if len(part) else None,
            "ic_t": t_of_mean(part["ic"]) if len(part) else None,
            "spread": float(part["spread"].mean()) if len(part) else None,
            "spread_t": t_of_mean(part["spread"]) if len(part) else None,
            "top_mean": float(part["top_mean"].mean()) if len(part) else None,
            "bottom_mean": float(part["bottom_mean"].mean()) if len(part) else None,
            "hit": float(part["hit"].mean()) if len(part) else None,
            "ic_rel": float(part["ic_rel"].dropna().mean()) if len(part) and part["ic_rel"].notna().any() else None,
        }
    years = []
    for year in sorted(stride.index.year.unique()):
        part = stride[stride.index.year == year]
        years.append({
            "year": int(year),
            "n": int(len(part)),
            "ic_mean": float(part["ic"].mean()) if len(part) else None,
            "spread": float(part["spread"].mean()) if len(part) else None,
        })
    out["by_year"] = years
    return out


def lookahead_holds(frames):
    """Perturb every value after the middle bar and assert the signal is unchanged."""
    name, (_, frame) = next(iter(frames.items()))
    t = len(frame) // 2
    funding = frame["funding_rate"].astype(float) if "funding_rate" in frame.columns else None
    oi = frame["oi_usd"].astype(float) if "oi_usd" in frame.columns else None
    checks = []
    if funding is not None and funding.notna().sum() > 30:
        signal = funding_signal(funding, 7)
        perturbed = funding.copy()
        perturbed.iloc[t + 1:] = perturbed.iloc[t + 1:] * 1.5
        other = funding_signal(perturbed, 7)
        before = signal.iloc[:t + 1]
        checks.append(bool(np.allclose(before.fillna(0), other.iloc[:t + 1].fillna(0), equal_nan=True)))
    if oi is not None and oi.notna().sum() > 30:
        signal = oi_signal(oi, 7)
        perturbed = oi.copy()
        perturbed.iloc[t + 1:] = perturbed.iloc[t + 1:] * 1.5
        other = oi_signal(perturbed, 7)
        before = signal.iloc[:t + 1]
        checks.append(bool(np.allclose(before.fillna(0), other.iloc[:t + 1].fillna(0), equal_nan=True)))
    return bool(checks) and all(checks)


def coverage(frames, column):
    """How many names actually hold the series, and when it ends."""
    spans = []
    for name, (_, frame) in frames.items():
        if column not in frame.columns:
            continue
        series = frame[column].dropna()
        if series.empty:
            continue
        spans.append((name, series.index.min(), series.index.max(), int(len(series))))
    if not spans:
        return {"names": 0}
    ends = [end for _, _, end, _ in spans]
    return {
        "names": len(spans),
        "earliest": min(start for _, start, _, _ in spans).strftime("%Y-%m-%d"),
        "latest_end": max(ends).strftime("%Y-%m-%d"),
        "ending_in_validation": sum(1 for end in ends if end >= pd.Timestamp("2024-07-01", tz="UTC")),
        "ending_in_test": sum(1 for end in ends if end >= pd.Timestamp("2026-01-01", tz="UTC")),
        "median_rows": int(sorted(n for _, _, _, n in spans)[len(spans) // 2]),
    }


def main():
    btc, frames = load_series()
    if not lookahead_holds(frames):
        raise SystemExit("lookahead check failed: the signal at t moves when later values change")
    cells = {}
    for family, column, signal_fn in (
        ("funding", "funding_rate", funding_signal),
        ("oi", "oi_usd", oi_signal),
    ):
        for window in WINDOWS:
            for horizon in HORIZONS:
                stacked = build(btc, frames, column, signal_fn, window, horizon)
                stats = daily_stats(stacked)
                cells[f"{family}_{window}_h{horizon}"] = summarise(stats, horizon)
    result = {
        "candidate": "xs_funding_oi",
        "written_at": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
        "panel_end": btc.index.max().strftime("%Y-%m-%d"),
        "btc_start": btc.index.min().strftime("%Y-%m-%d"),
        "names": len(frames) - 1,
        "funding_coverage": coverage(frames, "funding_rate"),
        "oi_coverage": coverage(frames, "oi_usd"),
        "round_trip_bps": ROUND_TRIP * 1e4,
        "funding_carry": "not subtracted; missing funding is never treated as zero",
        "lookahead": "pass",
        "primary": [f"{family}_{PRIMARY}_h{h}" for family in ("funding", "oi") for h in HORIZONS],
        "neighbours": [f"{family}_{w}_h{h}" for family in ("funding", "oi")
                       for w in WINDOWS if w != PRIMARY for h in HORIZONS],
        "cells": cells,
    }
    OUT.write_text(json.dumps(result, indent=1))
    print(f"wrote {OUT}")
    print(f"names {result['names']} panel_end {result['panel_end']}")
    print("funding", result["funding_coverage"])
    print("oi", result["oi_coverage"])
    for key in result["primary"]:
        cell = cells[key]
        val, test = cell["validation"], cell["test"]
        print(f"{key} dates={cell['n_dates']} names_median={cell['names_median']} "
              f"val n={val['n']} ic={val['ic_mean']} spread={val['spread']} "
              f"test n={test['n']} ic={test['ic_mean']} spread={test['spread']}")


if __name__ == "__main__":
    main()
