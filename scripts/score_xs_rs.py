"""Cross-sectional relative strength, the first single-feature test.

Pre-registered 2026-11-16T03:01:19Z in research/log.md. Reads data/panel_xs,
which the panel daemon already wrote, and scores nothing that was not named
in that pre-registration. No pull, no confirmation.

The signal at date t is the trailing return through t-1 minus BTC's own
trailing return through t-1. The target is the forward return starting at t.
Perturbing every close after t cannot move the signal at t, and the lookahead
check below asserts that.
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
OUT = ROOT / "results" / "2026-11-16_xs_relative_strength.json"

WINDOWS = (14, 30, 7, 21, 20, 45)
HORIZONS = (1, 3, 10)
PRIMARY = (14, 30)
MIN_NAMES = 20
# The panel has no USD open interest, so every name takes the thin tier.
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


def load_closes():
    """One close series per base, the venue with the longest history.

    A name is present on a date only when its file has a close that date, so
    a delisted name drops out on its last bar and a name not yet listed is
    absent rather than filled.
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
        frame = pd.read_csv(path, usecols=["date", "close"])
        frame = frame.dropna(subset=["close"])
        if frame.empty:
            continue
        frame["date"] = pd.to_datetime(frame["date"], utc=True).dt.normalize()
        close = frame.drop_duplicates("date").set_index("date")["close"].astype(float)
        close = close[close > 0]
        key = base_of(symbol)
        prior = candidates.get(key)
        if prior is None or len(close) > len(prior[1]):
            candidates[key] = (symbol, close)
    if "BTC" not in candidates:
        raise SystemExit("binance BTCUSDT is not in the panel")
    btc = candidates.pop("BTC")[1].sort_index()
    closes = {key: series.sort_index() for key, (_, series) in candidates.items()}
    return btc, closes


def trailing(close, window):
    """Return over the window ending yesterday. Bar t uses closes through t-1."""
    return close.shift(1) / close.shift(window + 1) - 1


def forward(close, horizon):
    """Return starting at today's close. Scoring uses this, never the level."""
    return close.shift(-horizon) / close - 1


def build(btc, closes, window, horizon):
    """Signal and net forward relative return, aligned on the common dates."""
    btc_trail = trailing(btc, window)
    btc_forward = forward(btc, horizon)
    frames = []
    for name, close in closes.items():
        signal = trailing(close, window) - btc_trail.reindex(close.index)
        gross = forward(close, horizon)
        relative = gross - btc_forward.reindex(close.index)
        frame = pd.DataFrame({
            "signal": signal,
            "relative": relative - ROUND_TRIP,
            "absolute": gross - ROUND_TRIP,
        }).dropna()
        frame["name"] = name
        frames.append(frame)
    stacked = pd.concat(frames)
    stacked.index.name = "date"
    return stacked


def daily_stats(stacked):
    """Rank correlation and decile spread per date, names present that date."""
    rows = []
    for date, group in stacked.groupby(level=0, sort=True):
        if len(group) < MIN_NAMES:
            continue
        signal = group["signal"]
        relative = group["relative"]
        if signal.nunique() < 2 or relative.nunique() < 2:
            continue
        ic = float(signal.rank().corr(relative.rank()))
        ranks = signal.rank(pct=True)
        top = relative[ranks >= 0.9]
        bottom = relative[ranks <= 0.1]
        if top.empty or bottom.empty:
            continue
        rows.append({
            "date": date,
            "names": int(len(group)),
            "ic": ic,
            "spread": float((top.mean() - bottom.mean()) * 100),
            "top_mean": float(top.mean() * 100),
            "bottom_mean": float(bottom.mean() * 100),
            "hit": float((relative > 0).mean()),
        })
    return pd.DataFrame(rows).set_index("date")


def t_of_mean(values):
    """t-stat of a mean against zero. Empty or flat returns NaN, not a claim."""
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


def summarise(stats, horizon):
    """Non-overlapping summary per period and per year."""
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


def lookahead_holds(btc, closes):
    """Perturb every close after the middle bar and assert the signal is unchanged."""
    name, close = next(iter(closes.items()))
    window = 14
    t = len(close) // 2
    signal = trailing(close, window) - trailing(btc, window).reindex(close.index)
    perturbed = close.copy()
    perturbed.iloc[t + 1:] = perturbed.iloc[t + 1:] * 1.5
    other = trailing(perturbed, window) - trailing(btc, window).reindex(close.index)
    before = signal.iloc[:t + 1]
    return bool(np.allclose(before.fillna(0), other.iloc[:t + 1].fillna(0), equal_nan=True))


def main():
    btc, closes = load_closes()
    if not lookahead_holds(btc, closes):
        raise SystemExit("lookahead check failed: the signal at t moves when later prices change")
    cells = {}
    for window in WINDOWS:
        for horizon in HORIZONS:
            stacked = build(btc, closes, window, horizon)
            stats = daily_stats(stacked)
            cells[f"rs_{window}_h{horizon}"] = summarise(stats, horizon)
    result = {
        "candidate": "xs_relative_strength",
        "written_at": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
        "panel_end": btc.index.max().strftime("%Y-%m-%d"),
        "btc_start": btc.index.min().strftime("%Y-%m-%d"),
        "names": len(closes),
        "round_trip_bps": ROUND_TRIP * 1e4,
        "funding_carry": "not subtracted; missing funding is never treated as zero",
        "lookahead": "pass",
        "primary": [f"rs_{w}_h{h}" for w in PRIMARY for h in HORIZONS],
        "neighbours": [f"rs_{w}_h{h}" for w in WINDOWS if w not in PRIMARY for h in HORIZONS],
        "cells": cells,
    }
    OUT.write_text(json.dumps(result, indent=1))
    print(f"wrote {OUT}")
    print(f"names {len(closes)} panel_end {result['panel_end']} btc_start {result['btc_start']}")
    for key in result["primary"]:
        cell = cells[key]
        val = cell["validation"]
        test = cell["test"]
        print(f"{key} dates={cell['n_dates']} names_median={cell['names_median']:.0f} "
              f"val n={val['n']} ic={val['ic_mean']} spread={val['spread']} "
              f"test n={test['n']} ic={test['ic_mean']} spread={test['spread']}")


if __name__ == "__main__":
    main()
