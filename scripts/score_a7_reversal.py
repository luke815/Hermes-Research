"""A7(1): 1-day and 3-day reversal on the Laevitas panel.

Pre-registered in research/backlog.md before this script existed. The commit
hash of that pre-registration is recorded in the payload. This script reads
data/panel_xs_laevitas, which is already on disk, and scores only the rule
named there. No pull, no confirmation.

The signal at date t is the negative of the return over the window ending
yesterday, so bar t uses closes through t-1. A name is in on a date only when
its file has a close that date and its prior-bar open interest clears the
floor. The book is built as matrix operations, one pass over the files.
Perturbing every value after t cannot move the signal or the vol scale at t,
and the lookahead check below asserts that.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from regime_tester.costs import (  # noqa: E402
    FUNDING_PERCENT_PER_SETTLEMENT, LIQUID_OI_USD, round_trip,
)
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
THIN = round_trip(None)
LIQUID = round_trip(LIQUID_OI_USD)

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


JUMP = 20


def drop_jumps(close):
    """A close more than 20x or less than 1/20 of both neighbours is a print.

    One bad day between two real ones is set to missing. Two bad days in a row
    are both set to missing: each is extreme against the real close on its
    other side and against the other bad day, so the rule has to look past the
    neighbour that is itself a print. The count is the days changed.
    """
    values = close.to_numpy(dtype=float).copy()
    changed = 0
    for col in range(values.shape[1]):
        series = values[:, col]
        bad = _jump_days(series)
        changed += int(bad.sum())
        series[bad] = np.nan
    out = pd.DataFrame(values, index=close.index, columns=close.columns)
    return out, changed


def _jump_days(series):
    bad = np.zeros(len(series), dtype=bool)
    changed = True
    while changed:
        changed = False
        for i in range(1, len(series) - 1):
            if np.isnan(series[i]) or bad[i]:
                continue
            left = _neighbour(series, i, -1, bad)
            right = _neighbour(series, i, 1, bad)
            if left is None or right is None:
                continue
            if _extreme(series[i], left) and _extreme(series[i], right):
                for j in range(len(series)):
                    if np.isnan(series[j]) or bad[j]:
                        continue
                    if not _extreme(series[j], series[i]):
                        bad[j] = True
                changed = True
    return bad


def _neighbour(series, i, step, bad):
    j = i + step
    while 0 <= j < len(series):
        if np.isnan(series[j]) or bad[j]:
            j += step
            continue
        if abs(series[j] - series[i]) / series[i] < 0.5:
            j += step
            continue
        return series[j]
    return None


def _extreme(value, other):
    return value > JUMP * other or value * JUMP < other


def load_matrices():
    """Close, prior-bar open interest and funding, one column per base coin.

    The longest file wins for a coin. A name is present on a date only when
    its file has a close that date. Nothing is filled forward. The columns are
    written into one array: aligning thousands of frames one at a time does
    not finish.
    """
    import time
    started = time.time()
    best = {}
    lengths = {}
    for n, path in enumerate(sorted(PANEL.glob("*.csv")), 1):
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
        frame = frame[frame["close"].astype(float) > 0]
        if frame.empty:
            continue
        key = base_of(symbol)
        prior = lengths.get(key, -1)
        if len(frame) > prior:
            best[key] = frame
            lengths[key] = len(frame)
        if n % 1000 == 0:
            print(f"read {n} {round(time.time() - started, 1)}s kept {len(best)}", flush=True)
    if "BTC" not in best:
        raise SystemExit("BTC is not in the panel")
    print(f"read done {round(time.time() - started, 1)}s kept {len(best)}", flush=True)
    dates = pd.DatetimeIndex(sorted(set().union(*(f.index for f in best.values()))))
    pos = {d: i for i, d in enumerate(dates)}
    names = sorted(best)
    n_dates, n_names = len(dates), len(names)
    close_a = np.full((n_dates, n_names), np.nan)
    oi_a = np.full((n_dates, n_names), np.nan)
    fund_a = np.full((n_dates, n_names), np.nan)
    for j, name in enumerate(names):
        frame = best[name]
        rows = np.fromiter((pos[d] for d in frame.index), dtype=int, count=len(frame))
        close_a[rows, j] = frame["close"].to_numpy(dtype=float)
        oi_a[rows, j] = frame["oi_usd"].to_numpy(dtype=float)
        if "funding_rate" in frame.columns:
            fund_a[rows, j] = frame["funding_rate"].to_numpy(dtype=float)
    close = pd.DataFrame(close_a, index=dates, columns=names)
    close, changed = drop_jumps(close)
    print(f"jumps dropped {changed}", flush=True)
    oi = pd.DataFrame(oi_a, index=dates, columns=names).shift(1)
    funding = pd.DataFrame(fund_a, index=dates, columns=names)
    print(f"aligned {close.shape} {round(time.time() - started, 1)}s", flush=True)
    return close, oi, funding


def loser_signal(close, window):
    """Negative of the return over `window` bars ending yesterday."""
    return -(close.shift(1) / close.shift(window + 1) - 1)


def vol_scale(close):
    """Inverse trailing 30-day vol, known at t-1. Short histories stay empty."""
    vol = close.pct_change().rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std().shift(1)
    return 1.0 / vol.where(vol > 0)


def window_sum(values, horizon):
    """Sum of values[i : i + horizon] at each i. A missing day leaves it empty."""
    arr = values.to_numpy(dtype=float)
    filled = np.where(np.isnan(arr), 0.0, arr)
    csum = np.vstack([np.zeros((1, arr.shape[1])), np.cumsum(filled, axis=0)])
    valid = np.vstack([np.zeros((1, arr.shape[1]), dtype=int),
                       np.cumsum(np.isnan(arr).astype(int), axis=0)])
    end = np.arange(horizon - 1, len(arr))
    start = end - (horizon - 1)
    total = csum[end + 1] - csum[start]
    missing = valid[end + 1] - valid[start]
    out = np.full(arr.shape, np.nan)
    out[end] = np.where(missing == 0, total, np.nan)
    return pd.DataFrame(out, index=values.index, columns=values.columns)


def net_return(close, funding, oi, horizon):
    """Gross and net forward return. A missing carry leaves the net missing."""
    gross = close.shift(-horizon) / close - 1
    cost = pd.DataFrame(np.where(oi.shift(0).to_numpy() >= LIQUID_OI_USD, LIQUID, THIN),
                        index=close.index, columns=close.columns)
    # The tier uses the prior bar, which `oi` already is. A missing tier takes
    # the thin rate, matching costs.round_trip.
    cost = cost.where(oi.notna(), THIN)
    carry = window_sum(funding / FUNDING_PERCENT_PER_SETTLEMENT, horizon)
    return gross, gross - cost - carry


def daily_stats(signal, scale, oi, gross, net, floor):
    """Vol-scaled decile spread on names clearing the floor that day.

    Ranks are one matrix operation. A date with fewer than 20 names above the
    floor is skipped, and a leg shorter than 5 names is skipped.
    """
    sig = signal.to_numpy(dtype=float)
    sc = scale.to_numpy(dtype=float)
    gr = gross.to_numpy(dtype=float)
    nt = net.to_numpy(dtype=float)
    oi_v = oi.to_numpy(dtype=float)
    ok = (np.isfinite(sig) & np.isfinite(sc) & np.isfinite(gr) & np.isfinite(nt)
          & np.isfinite(oi_v) & (oi_v >= floor))
    ranked = pd.DataFrame(np.where(ok, sig, np.nan), index=signal.index).rank(
        axis=1, pct=True, method="average")
    pct = ranked.to_numpy(dtype=float)
    long_m = ok & (pct >= 0.9)
    short_m = ok & (pct <= 0.1)
    count = ok.sum(axis=1)
    long_n = long_m.sum(axis=1)
    short_n = short_m.sum(axis=1)
    keep = (count >= MIN_NAMES) & (long_n >= MIN_LEG) & (short_n >= MIN_LEG)

    def weighted(values, mask):
        w = np.where(mask, sc, 0.0)
        total = w.sum(axis=1)
        total = np.where(total > 0, total, np.nan)
        return (np.where(mask, values, 0.0) * w).sum(axis=1) / total

    ln = weighted(nt, long_m)
    sn = weighted(nt, short_m)
    lg = weighted(gr, long_m)
    sg = weighted(gr, short_m)
    good = keep & np.isfinite(ln) & np.isfinite(sn)
    idx = signal.index[good]
    stats = pd.DataFrame({
        "names": count[good],
        "spread_net": (ln[good] - sn[good]) * 100,
        "spread_gross": (lg[good] - sg[good]) * 100,
        "long_net": ln[good] * 100,
        "short_net": sn[good] * 100,
        "hit": (ln[good] > sn[good]).astype(float),
    }, index=idx)
    stats.index.name = "date"
    return stats, {"dates_seen": int(sig.shape[0]), "dates_kept": int(good.sum())}


def t_of_mean(values):
    """t-stat of a mean against zero. Empty or flat returns None."""
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    if len(values) < 3 or values.std(ddof=1) == 0:
        return None
    return float(values.mean() / (values.std(ddof=1) / np.sqrt(len(values))))


def period_mask(index):
    dates = index.tz_convert("UTC")
    out = {}
    for name, start, end in PERIODS:
        mask = pd.Series(True, index=index)
        if start is not None:
            mask &= dates >= pd.Timestamp(start, tz="UTC")
        if end is not None:
            mask &= dates <= pd.Timestamp(end, tz="UTC")
        out[name] = mask
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
    masks = period_mask(stride.index)
    out["n_dates"] = int(len(stride))
    out["names_median"] = float(stride["names"].median())
    for name, _, _ in PERIODS:
        part = stride[masks[name]]
        out[name] = {
            "n": int(len(part)),
            "spread_net": None if part.empty else float(part["spread_net"].mean()),
            "spread_gross": None if part.empty else float(part["spread_gross"].mean()),
            "spread_t": None if part.empty else t_of_mean(part["spread_net"]),
            "long_net": None if part.empty else float(part["long_net"].mean()),
            "short_net": None if part.empty else float(part["short_net"].mean()),
            "hit": None if part.empty else float(part["hit"].mean()),
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
    if (held[0]["spread_net"] > 0) != (held[1]["spread_net"] > 0):
        return "rejected"
    if any(abs(part["spread_t"]) < T_BAR for part in held):
        return "insufficient"
    return "admitted"


def lookahead_ok(close):
    """Perturb every close after a mid date and rebuild. The signal and the
    vol scale at and before that date must not move."""
    mid = close.index[len(close) // 2]
    shifted = close.copy()
    shifted.loc[shifted.index > mid] = shifted.loc[shifted.index > mid] * 1.5
    before = loser_signal(close, 1)
    after = loser_signal(shifted, 1)
    scale_before = vol_scale(close)
    scale_after = vol_scale(shifted)
    same_signal = before.loc[:mid].equals(after.loc[:mid])
    same_scale = scale_before.loc[:mid].equals(scale_after.loc[:mid])
    return bool(same_signal and same_scale), str(mid.date())


def main():
    close, oi, funding = load_matrices()
    held, mid = lookahead_ok(close)
    print(f"lookahead {held} at {mid}", flush=True)
    if not held:
        raise SystemExit(f"lookahead failed at {mid}")
    btc = close["BTC"]
    scale = vol_scale(close)
    cells = []
    for window in WINDOWS:
        signal = loser_signal(close, window)
        for horizon in HORIZONS:
            gross, net = net_return(close, funding, oi, horizon)
            excess = gross.sub(btc.shift(-horizon) / btc - 1, axis=0)
            for floor in FLOORS:
                stats, coverage = daily_stats(signal, scale, oi, excess, net, floor)
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
                print(f"cell w{window} h{horizon} floor {floor} kept {coverage['dates_kept']}", flush=True)
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
        "names": int(close.shape[1]),
        "rows": int(close.shape[0]),
        "lookahead": {"passed": held, "cut": mid},
        "cells": cells,
        "verdicts": verdicts,
        "verdict": overall,
    }
    path = write_result("a7_reversal", payload, inputs=["data/panel_xs_laevitas"])
    print(json.dumps({"names": int(close.shape[1]), "verdicts": verdicts, "verdict": overall}))
    print(path)


if __name__ == "__main__":
    main()
