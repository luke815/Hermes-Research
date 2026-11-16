"""One-day reversal in the bottom half of the universe by open interest.

Pre-registered 2026-11-16T05:01:47Z in research/log.md. Reads data/panel_xs,
which is already on disk, and scores only the signal named there.
No pull, no confirmation.

The signal at date t is the negative of the return over the window ending
yesterday, so bar t uses closes through t-1 and never today's close. The
universe on a date is the names whose prior-bar USD open interest sits at
or below that date's own cut. A missing open-interest value leaves the name
out of the ranking that date. Perturbing every value after t cannot move the
signal at t, and the lookahead check below asserts that.
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
OUT = ROOT / "results" / "2026-11-16_xs_reversal_1d.json"

WINDOWS = (1, 2, 3)
HORIZONS = (1, 3, 10)
PRIMARY_WINDOW = 1
PRIMARY_HORIZON = 1
# The bottom half is the primary cut. Neighbours are the bottom third and
# the bottom two thirds, all cut on the same prior-bar open interest.
CUTS = {"bottom_half": 0.5, "bottom_third": 1 / 3, "bottom_two_thirds": 2 / 3}
PRIMARY_CUT = "bottom_half"
# A date needs 20 names with open interest before a half of it can be ranked,
# and the half itself needs 10 names before a rank correlation means anything.
MIN_UNIVERSE = 20
MIN_HALF = 10
# Open interest is saved for stopped names only, so the live names have no
# USD open interest and every name takes the thin tier.
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


def load_frames():
    """Close, open interest and funding per base, longest history wins.

    A name is present on a date only when its file has a close that date.
    Open interest and funding are never filled forward and never set to zero.
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
        if "close" not in header:
            continue
        wanted = [c for c in ("date", "close", "oi_usd", "funding_rate") if c in header]
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
    return candidates["BTC"][1]["close"], candidates


def loser_signal(close, window):
    """Negative of the return over `window` bars ending yesterday.

    A higher value is the bigger loser. The shift puts bar t on closes
    through t-1, so today's close never enters the signal.
    """
    return -(close.shift(1) / close.shift(window + 1) - 1)


def forward(close, horizon):
    """Return starting at today's close. Scoring uses this, never the level."""
    return close.shift(-horizon) / close - 1


def build(btc, frames, window, horizon):
    """Signal, prior-bar open interest and net forward return, per name."""
    btc_forward = forward(btc, horizon)
    rows = []
    for name, (_, frame) in frames.items():
        if "oi_usd" not in frame.columns:
            continue
        signal = loser_signal(frame["close"], window)
        gross = forward(frame["close"], horizon)
        relative = gross - btc_forward.reindex(frame.index)
        out = pd.DataFrame({
            "signal": signal,
            "oi": frame["oi_usd"].astype(float).shift(1),
            "absolute": gross - ROUND_TRIP,
            "relative": relative - ROUND_TRIP,
        }).dropna(subset=["signal", "oi", "absolute"])
        if out.empty:
            continue
        out["name"] = name
        rows.append(out)
    if not rows:
        return pd.DataFrame()
    stacked = pd.concat(rows)
    stacked.index.name = "date"
    return stacked


def daily_stats(stacked, cut):
    """Rank correlation and decile spread inside the open-interest cut."""
    if stacked.empty:
        return pd.DataFrame(), {"dates_with_oi": 0, "dates_kept": 0}
    rows = []
    seen = 0
    for date, group in stacked.groupby(level=0, sort=True):
        seen += 1
        if len(group) < MIN_UNIVERSE:
            continue
        threshold = group["oi"].quantile(cut)
        half = group[group["oi"] <= threshold]
        if len(half) < MIN_HALF:
            continue
        signal = half["signal"]
        absolute = half["absolute"]
        relative = half["relative"]
        if signal.nunique() < 2 or absolute.nunique() < 2:
            continue
        ic = float(signal.rank().corr(absolute.rank()))
        ranks = signal.rank(pct=True)
        top = absolute[ranks >= 0.9]
        bottom = absolute[ranks <= 0.1]
        if top.empty or bottom.empty:
            continue
        both = relative.notna()
        ic_rel = (
            float(signal[both].rank().corr(relative[both].rank()))
            if both.sum() >= MIN_HALF else None
        )
        rows.append({
            "date": date,
            "names": int(len(half)),
            "universe": int(len(group)),
            "ic": ic,
            "spread": float((top.mean() - bottom.mean()) * 100),
            "top_mean": float(top.mean() * 100),
            "bottom_mean": float(bottom.mean() * 100),
            "hit": float((absolute > 0).mean()),
            "ic_relative": ic_rel,
        })
    stats = pd.DataFrame(rows)
    if not stats.empty:
        stats = stats.set_index("date")
    return stats, {"dates_with_oi": int(seen), "dates_kept": int(len(stats))}


def t_of_mean(values):
    """t-stat of a mean against zero. Empty or flat returns None, not a claim."""
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
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


def summarise(stats, horizon, coverage):
    """Non-overlapping summary per period and per year."""
    out = {"n_dates": 0, "names_median": None, "coverage": coverage}
    if stats.empty:
        for name, _, _ in PERIODS:
            out[name] = {"n": 0}
        out["by_year"] = []
        return out
    stride = stats.iloc[::horizon]
    periods = period_of(stride.index)
    out["n_dates"] = int(len(stride))
    out["names_median"] = float(stride["names"].median())
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
            "ic_relative": (
                float(part["ic_relative"].dropna().mean())
                if part["ic_relative"].notna().any() else None
            ),
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
    """Perturb every close after the middle bar and assert the signal is unchanged."""
    frame = next(part for _, part in frames.values() if len(part) > 10)
    close = frame["close"]
    t = len(close) // 2
    signal = loser_signal(close, PRIMARY_WINDOW)
    perturbed = close.copy()
    perturbed.iloc[t + 1:] = perturbed.iloc[t + 1:] * 1.5
    other = loser_signal(perturbed, PRIMARY_WINDOW)
    before = signal.iloc[:t + 1]
    return bool(np.allclose(before.fillna(0), other.iloc[:t + 1].fillna(0), equal_nan=True))


def inventory(frames):
    """How much open interest the panel actually holds, so the gap is visible."""
    oi_names = 0
    latest = None
    reach_test = 0
    for _, frame in frames.values():
        if "oi_usd" not in frame.columns or frame["oi_usd"].notna().sum() == 0:
            continue
        oi_names += 1
        last = frame.index[frame["oi_usd"].notna()].max()
        latest = last if latest is None or last > latest else latest
        if last >= pd.Timestamp("2026-01-01", tz="UTC"):
            reach_test += 1
    return {
        "names_with_oi": oi_names,
        "oi_latest": latest.strftime("%Y-%m-%d") if latest is not None else None,
        "oi_names_reaching_test": reach_test,
    }


def main():
    btc, frames = load_frames()
    if not lookahead_holds(frames):
        raise SystemExit("lookahead check failed: the signal at t moves when later prices change")
    cells = {}
    for cut_name, cut in CUTS.items():
        for window in WINDOWS:
            for horizon in HORIZONS:
                stacked = build(btc, frames, window, horizon)
                stats, coverage = daily_stats(stacked, cut)
                cells[f"rev_{cut_name}_w{window}_h{horizon}"] = summarise(stats, horizon, coverage)
    result = {
        "candidate": "xs_reversal_1d",
        "written_at": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
        "panel_end": btc.index.max().strftime("%Y-%m-%d"),
        "btc_start": btc.index.min().strftime("%Y-%m-%d"),
        "names": len(frames) - 1,
        "open_interest": inventory(frames),
        "round_trip_bps": ROUND_TRIP * 1e4,
        "funding_carry": "not subtracted; missing funding is never treated as zero",
        "lookahead": "pass",
        "primary": [f"rev_{PRIMARY_CUT}_w{PRIMARY_WINDOW}_h{h}" for h in HORIZONS],
        "cells": cells,
    }
    OUT.write_text(json.dumps(result, indent=1))
    print(f"wrote {OUT}")
    print(f"names {result['names']} oi {result['open_interest']} panel_end {result['panel_end']}")
    for key, cell in cells.items():
        print(f"{key} dates={cell['n_dates']} kept={cell['coverage']['dates_kept']} "
              f"of {cell['coverage']['dates_with_oi']}")


if __name__ == "__main__":
    main()
