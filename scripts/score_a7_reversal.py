"""A7(1): 1-day and 3-day reversal on the Laevitas panel.

Pre-registered in research/backlog.md before this script existed. The commit
hash of that pre-registration is recorded in the payload. This script reads
data/panel_xs_laevitas, which is already on disk, and scores only the rule
named there. No pull, no confirmation.

The signal at date t is the negative of the return over the window ending
yesterday, so bar t uses closes through t-1. A name is in on a date only when
its file has a close that date and its prior-bar open interest clears the
floor. Perturbing every value after t cannot move the signal or the vol scale
at t, and the lookahead check below asserts that.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from regime_tester.costs import apply_costs  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PANEL = ROOT / "data" / "panel_xs_laevitas"
PREREG_COMMIT = "2d7883299780a534cbbdaf1ab529afe51b19d835"

WINDOWS = (1, 3)
HORIZONS = (1, 3)
FLOORS = (10_000_000, 20_000_000, 50_000_000)
PRIMARY_FLOOR = 20_000_000
VOL_WINDOW = 30
MIN_NAMES = 20
MIN_LEG = 5
T_BAR = 2.0
N_BAR = 40

PERIODS = (
    ("train", None, "2024-06-30"),
    ("validation", "2024-07-01", "2025-12-31"),
    ("test", "2026-01-01", None),
)


def base_of(symbol):
    """Strip the quote and the venue suffix so the same coin collapses."""
    stem = symbol.split(".")[0]
    for suffix in ("_PERP", "-SWAP", "USDT", "USDC", "USD"):
        if stem.endswith(suffix) and len(stem) > len(suffix):
            stem = stem[: -len(suffix)]
            break
    return stem


def load_frames():
    """Close, open interest and funding per base, longest history wins.

    A name is present on a date only when its file has a close that date.
    Open interest and funding are never filled forward and never set to zero.
    """
    candidates = {}
    for path in sorted(PANEL.glob("*.csv")):
        symbol = path.name.split("_", 1)[1][:-4]
        header = path.read_text(encoding="utf-8").split("\n", 1)[0].split(",")
        if "close" not in header or "oi_usd" not in header:
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
        if frame.empty:
            continue
        key = base_of(symbol)
        prior = candidates.get(key)
        if prior is None or len(frame) > len(prior[1]):
            candidates[key] = (symbol, frame)
    if "BTC" not in candidates:
        raise SystemExit("BTC is not in the panel")
    return candidates["BTC"][1]["close"], candidates


def loser_signal(close, window):
    """Negative of the return over `window` bars ending yesterday."""
    return -(close.shift(1) / close.shift(window + 1) - 1)


def vol_scale(close):
    """Inverse of the trailing 30-day realized vol, known at t-1.

    The last return inside the window ends yesterday, so today's close never
    enters the scale. A name with fewer than 30 returns is left out.
    """
    ret = close.pct_change()
    vol = ret.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std().shift(1)
    return 1.0 / vol.where(vol > 0)


def build(btc, frames, window, horizon):
    """Signal, prior-bar open interest, vol scale and net forward return."""
    btc_forward = btc.shift(-horizon) / btc - 1
    rows = []
    for name, (_, frame) in frames.items():
        signal = loser_signal(frame["close"], window)
        scale = vol_scale(frame["close"])
        funding = frame["funding_rate"] if "funding_rate" in frame.columns else None
        costs = apply_costs(frame["close"], horizon, side=1,
                            funding=funding, oi_usd=frame["oi_usd"])
        relative = costs["gross"] - btc_forward.reindex(frame.index)
        out = pd.DataFrame({
            "signal": signal,
            "oi": frame["oi_usd"].astype(float).shift(1),
            "scale": scale,
            "gross": costs["gross"],
            "net": costs["net"],
            "relative_net": relative - costs["round_trip"] - costs["carry"],
        }).dropna(subset=["signal", "oi", "scale", "net"])
        if out.empty:
            continue
        out["name"] = name
        rows.append(out)
    if not rows:
        return pd.DataFrame()
    stacked = pd.concat(rows)
    stacked.index.name = "date"
    return stacked


def daily_stats(stacked, floor):
    """Decile spread inside the open-interest floor, vol-scaled."""
    if stacked.empty:
        return pd.DataFrame(), {"dates_seen": 0, "dates_kept": 0}
    rows = []
    seen = 0
    for date, group in stacked.groupby(level=0, sort=True):
        seen += 1
        liquid = group[group["oi"] >= floor]
        if len(liquid) < MIN_NAMES:
            continue
        signal = liquid["signal"]
        if signal.nunique() < 2:
            continue
        ranks = signal.rank(pct=True)
        top = liquid[ranks >= 0.9]
        bottom = liquid[ranks <= 0.1]
        if len(top) < MIN_LEG or len(bottom) < MIN_LEG:
            continue
        # Long the losers (top of the negated signal), short the winners.
        long_w = top["scale"] / top["scale"].sum()
        short_w = bottom["scale"] / bottom["scale"].sum()
        long_net = float((top["net"] * long_w).sum())
        short_net = float((bottom["net"] * short_w).sum())
        long_gross = float((top["gross"] * long_w).sum())
        short_gross = float((bottom["gross"] * short_w).sum())
        rows.append({
            "date": date,
            "names": int(len(liquid)),
            "spread_net": (long_net - short_net) * 100,
            "spread_gross": (long_gross - short_gross) * 100,
            "long_net": long_net * 100,
            "short_net": short_net * 100,
            "hit": float(long_net > short_net),
        })
    stats = pd.DataFrame(rows)
    if not stats.empty:
        stats = stats.set_index("date")
    return stats, {"dates_seen": int(seen), "dates_kept": int(len(stats))}


def t_of_mean(values):
    """t-stat of a mean against zero. Empty or flat returns None."""
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
    out = {"n_dates": 0}
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
            "spread_net": float(part["spread_net"].mean()) if len(part) else None,
            "spread_gross": float(part["spread_gross"].mean()) if len(part) else None,
            "spread_t": t_of_mean(part["spread_net"]) if len(part) else None,
            "long_net": float(part["long_net"].mean()) if len(part) else None,
            "short_net": float(part["short_net"].mean()) if len(part) else None,
            "hit": float(part["hit"].mean()) if len(part) else None,
        }
    by_year = []
    for year, part in stride.groupby(stride.index.year):
        by_year.append({
            "year": int(year),
            "n": int(len(part)),
            "spread_net": float(part["spread_net"].mean()),
            "spread_t": t_of_mean(part["spread_net"]),
        })
    out["by_year"] = by_year
    return out


def verdict_of(summary):
    """Admitted, rejected or insufficient, from the pre-registered pass rule."""
    held = []
    for name in ("validation", "test"):
        part = summary[name]
        if part["n"] < N_BAR or part["spread_t"] is None:
            return "insufficient"
        held.append(part)
    signs = [part["spread_net"] > 0 for part in held]
    if signs[0] != signs[1]:
        return "rejected"
    if any(abs(part["spread_t"]) < T_BAR for part in held):
        return "insufficient"
    return "admitted"


def lookahead_ok(frames):
    """Perturb every close after a mid date and rebuild. The signal at and
    before that date must not move. A failing check exits rather than scoring."""
    name, (_, frame) = next(iter(frames.items()))
    mid = frame.index[len(frame) // 2]
    shifted = frame.copy()
    shifted.loc[shifted.index > mid, "close"] = shifted.loc[shifted.index > mid, "close"] * 1.5
    before = loser_signal(frame["close"], 1)
    after = loser_signal(shifted["close"], 1)
    scale_before = vol_scale(frame["close"])
    scale_after = vol_scale(shifted["close"])
    same_signal = before.loc[:mid].equals(after.loc[:mid])
    same_scale = scale_before.loc[:mid].equals(scale_after.loc[:mid])
    return bool(same_signal and same_scale), str(mid.date()), name


def main():
    btc, frames = load_frames()
    held, mid, checked = lookahead_ok(frames)
    if not held:
        raise SystemExit(f"lookahead failed on {checked} at {mid}")
    cells = []
    for window in WINDOWS:
        for horizon in HORIZONS:
            stacked = build(btc, frames, window, horizon)
            for floor in FLOORS:
                stats, coverage = daily_stats(stacked, floor)
                summary = summarise(stats, horizon)
                cells.append({
                    "window": window,
                    "horizon": horizon,
                    "floor": floor,
                    "primary": floor == PRIMARY_FLOOR,
                    "coverage": coverage,
                    "summary": summary,
                    "verdict": verdict_of(summary) if floor == PRIMARY_FLOOR else "neighbour",
                })
    primary = [c for c in cells if c["primary"]]
    verdicts = {f"w{c['window']}_h{c['horizon']}": c["verdict"] for c in primary}
    if all(v == "admitted" for v in verdicts.values()):
        overall = "admitted"
    elif any(v == "rejected" for v in verdicts.values()):
        overall = "rejected"
    else:
        overall = "insufficient"
    payload = {
        "candidate": "a7_reversal",
        "panel": "data/panel_xs_laevitas",
        "prereg_commit": PREREG_COMMIT,
        "names": len(frames),
        "lookahead": {"passed": held, "cut": mid, "name": checked},
        "cells": cells,
        "verdicts": verdicts,
        "verdict": overall,
    }
    path = write_result("a7_reversal", payload, inputs=["data/panel_xs_laevitas"])
    print(json.dumps({"names": len(frames), "verdicts": verdicts, "verdict": overall}))
    print(path)


if __name__ == "__main__":
    main()
