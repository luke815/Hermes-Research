"""One measure of the train-only sweep, shared by the one-shot scorer and the daemon.

The rules are the ones pre-registered for S3. Bars are cut at the train end
before any indicator is computed, features are lagged one bar, and percentiles
come from past data only. Nothing here reads validation or test.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from regime_tester.costs import apply_costs
from regime_tester.indicators import LIBRARY_VERSION, indicators

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

TRAIN_END = np.datetime64("2024-06-30")
MIN_INDEPENDENT = 40
WINDOW = 252
MIN_RANK = 30
DUPLICATE_CORR = 0.7
MAJORS = ["ETH", "SOL", "XRP", "BNB", "DOGE", "ADA", "AVAX", "LINK", "DOT",
          "LTC", "BCH", "NEAR", "APT", "SUI", "ARB", "OP", "FIL", "ATOM", "UNI"]
ADMITTED = ["btc_ret_30", "btc_vol_z90", "btc_trend_stretch", "eth_funding_z30"]

NEIGHBOURS = {5: (1, 10), 10: (5, 15), 20: (15, 25),
              80: (75, 85), 90: (85, 95), 95: (90, 99)}
TRANSFORMS = ["raw", "pct_252", "z_30", "z_90", "chg_3", "chg_7", "chg_30",
              "persistence", "acceleration"]
THRESHOLDS = [80, 90, 95, 20, 10, 5]
TARGETS = ["ret_1", "ret_3", "ret_10", "rel_1", "rel_3", "rel_10"]
UNIVERSES = ["btc", "eth", "pooled_majors"]


def load_frames():
    """Daily OHLC and funding for the 20 names, cut at the train end.

    The cut happens before any indicator is computed, so a later price cannot
    move an early bar. The funding file's symbol map is empty, so both files
    are keyed through the ohlcv map, which carries the 20 names used here.
    """
    ohlcv = json.loads((RAW / "coinalyze_ohlcv-history.json").read_text())
    funding = json.loads((RAW / "coinalyze_funding-rate-history.json").read_text())
    inverse = {v: k for k, v in ohlcv["symbols"].items()}
    frames = {}
    for series in ohlcv["data"]:
        token = inverse[series["symbol"]]
        rows = {bar["t"]: bar for bar in series["history"]}
        frame = pd.DataFrame.from_dict(rows, orient="index").sort_index()
        frame.index = pd.to_datetime(frame.index, unit="s", utc=True)
        frame = frame.rename(columns={"o": "open", "h": "high", "l": "low",
                                      "c": "close", "v": "volume"})
        frames[token] = frame[["open", "high", "low", "close", "volume"]].astype(float)
    fund = {}
    for series in funding["data"]:
        token = inverse.get(series["symbol"])
        if token is None:
            continue
        s = pd.Series({bar["t"]: bar.get("c") for bar in series["history"]}, dtype=float)
        s.index = pd.to_datetime(s.index, unit="s", utc=True)
        fund[token] = s.sort_index()
    cutoff = pd.Timestamp(TRAIN_END, tz="UTC")
    for token in frames:
        frames[token] = frames[token].loc[:cutoff]
        if token in fund:
            frames[token]["funding"] = fund[token].reindex(frames[token].index)
    # Every name is aligned to BTC's dates. A name that listed later keeps
    # empty bars before its first trade, so a pooled cell compares the same
    # days and a relative return subtracts BTC on the same bar.
    base = frames["BTC"].index
    for token in frames:
        frames[token] = frames[token].reindex(base)
    return frames


def rolling_rank(values, window=WINDOW, min_periods=MIN_RANK):
    """Percentile of each bar within its own trailing window, in 0..100.

    The window ends at the bar. Callers lag the result, so bar t is scored
    against a window that excludes bar t.
    """
    a = np.asarray(values, dtype=float)
    n = len(a)
    out = np.full(n, np.nan)
    for i in range(min_periods - 1, n):
        if np.isnan(a[i]):
            continue
        w = a[max(0, i - window + 1):i + 1]
        w = w[~np.isnan(w)]
        if len(w) < min_periods:
            continue
        out[i] = 100.0 * np.sum(w <= a[i]) / len(w)
    return out


def rolling_mean_std(values, window):
    a = np.asarray(values, dtype=float)
    c = np.cumsum(np.where(np.isnan(a), 0.0, a))
    c2 = np.cumsum(np.where(np.isnan(a), 0.0, a * a))
    k = np.cumsum(~np.isnan(a))
    n = len(a)
    mean = np.full(n, np.nan)
    std = np.full(n, np.nan)
    for i in range(window - 1, n):
        lo = i - window
        count = k[i] - (k[lo] if lo >= 0 else 0)
        if count < window:
            continue
        total = c[i] - (c[lo] if lo >= 0 else 0)
        total2 = c2[i] - (c2[lo] if lo >= 0 else 0)
        m = total / count
        var = total2 / count - m * m
        mean[i] = m
        std[i] = np.sqrt(var) if var > 0 else np.nan
    return mean, std


def transform(values, name):
    """One trailing transform. Early bars stay empty."""
    a = np.asarray(values, dtype=float)
    if name == "raw":
        return a
    if name == "pct_252":
        return rolling_rank(a)
    if name in ("z_30", "z_90"):
        w = 30 if name == "z_30" else 90
        mean, std = rolling_mean_std(a, w)
        return (a - mean) / std
    if name.startswith("chg_"):
        w = int(name.split("_")[1])
        out = np.full(len(a), np.nan)
        base = a[:-w]
        with np.errstate(divide="ignore", invalid="ignore"):
            out[w:] = np.where(base != 0, a[w:] / base - 1, np.nan)
        return out
    if name == "persistence":
        rank = rolling_rank(a)
        above = rank >= 80
        out = np.zeros(len(a))
        run = 0
        for i in range(len(a)):
            run = run + 1 if above[i] else 0
            out[i] = run
        return out
    if name == "acceleration":
        d = np.diff(a, prepend=np.nan)
        out = np.full(len(a), np.nan)
        out[6:] = d[6:] - d[1:-5]
        return out
    raise ValueError(name)


def newey_west_t(x, lag):
    """t-stat of a mean with Newey-West standard error, lag equal to horizon."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 3:
        return np.nan
    mean = x.mean()
    d = x - mean
    gamma0 = np.dot(d, d) / n
    var = gamma0
    for k in range(1, min(lag, n - 1) + 1):
        var += 2 * (1 - k / (lag + 1)) * np.dot(d[k:], d[:-k]) / n
    se = np.sqrt(max(var, 0) / n)
    return float(mean / se) if se else np.nan


def score_signal(signal, forward, horizon, years):
    """Signalled minus unsignalled, on all bars and on every h-th bar."""
    valid = (~np.isnan(forward)) & (signal >= 0)
    if valid.sum() < MIN_INDEPENDENT:
        return None
    sig = valid & (signal == 1)
    uns = valid & (signal == 0)
    if not sig.any() or not uns.any():
        return None
    spread = float(forward[sig].mean() - forward[uns].mean())
    stride = np.zeros(len(forward), dtype=bool)
    first = int(np.argmax(valid))
    stride[first::horizon] = True
    sig_i = sig & stride
    uns_i = uns & stride
    spread_i = (float(forward[sig_i].mean() - forward[uns_i].mean())
                if sig_i.any() and uns_i.any() else np.nan)
    gap = np.where(sig, forward - forward[uns].mean(), np.nan)
    year_signs = {}
    for year, mask in years.items():
        a = sig_i & mask
        b = uns_i & mask
        if a.any() and b.any():
            year_signs[year] = float(np.sign(forward[a].mean() - forward[b].mean()))
    return {
        "spread": spread,
        "spread_independent": spread_i,
        "t_newey_west": newey_west_t(gap, horizon),
        "n_independent": int(min(sig_i.sum(), uns_i.sum())),
        "n_overlap": int(valid.sum()),
        "year_signs": year_signs,
    }


def spread_only(signal, forward, horizon):
    """Independent spread alone, for the neighbour check."""
    valid = (~np.isnan(forward)) & (signal >= 0)
    if not valid.any():
        return np.nan
    first = int(np.argmax(valid))
    stride = np.zeros(len(forward), dtype=bool)
    stride[first::horizon] = True
    sig = valid & (signal == 1) & stride
    uns = valid & (signal == 0) & stride
    if not sig.any() or not uns.any():
        return np.nan
    return float(forward[sig].mean() - forward[uns].mean())


def cell_id(measure, transform_name, direction, threshold, target, universe):
    return "|".join([measure, transform_name, direction, str(threshold), target,
                      universe, "none", "daily"])


def train_hash(frames):
    return hashlib.sha256(
        f"{TRAIN_END}|{len(frames['BTC'])}|{frames['BTC'].index.max().date()}".encode()
    ).hexdigest()[:16]


def prepare():
    """Frames, indicators and the admitted factors, all cut at the train end."""
    frames = load_frames()
    if any(f.index.max() > pd.Timestamp("2024-06-30", tz="UTC") for f in frames.values()):
        raise RuntimeError("a frame holds a bar after the train end")
    computed = {token: indicators(frame) for token, frame in frames.items()}
    btc = frames["BTC"]
    admitted = {
        "btc_ret_30": btc["close"].pct_change(30).to_numpy(),
        "btc_vol_z90": transform(btc["close"].pct_change().rolling(30).std().to_numpy(), "z_90"),
        "btc_trend_stretch": (btc["close"] / btc["close"].rolling(200).mean() - 1).to_numpy(),
        "eth_funding_z30": transform(frames["ETH"]["funding"].to_numpy(), "z_30"),
    }
    years = {token: {int(y): (frame.index.year == y)
                     for y in sorted(set(frame.index.year))}
             for token, frame in frames.items()}
    return frames, computed, admitted, years, train_hash(frames)


def score_measure(measure, frames, computed, admitted, years, period_hash, done):
    """Rows for one measure, skipping cell ids already saved. Empty if none."""
    holders = [t for t in frames if measure in computed[t].columns]
    if not holders:
        return []
    net_cache = {}

    def forward(token, horizon, relative):
        key = (token, horizon, relative)
        if key not in net_cache:
            net = apply_costs(frames[token]["close"], horizon, side=1,
                              funding=frames[token]["funding"])["net"].to_numpy()
            if relative:
                base = apply_costs(frames["BTC"]["close"], horizon, side=1,
                                   funding=frames["BTC"]["funding"])["net"].to_numpy()
                net = net - base
            net_cache[key] = net
        return net_cache[key]

    rows = []
    for transform_name in TRANSFORMS:
        transformed = {t: transform(computed[t][measure].to_numpy(), transform_name)
                       for t in holders}
        lagged = {t: np.concatenate([[np.nan], v[:-1]]) for t, v in transformed.items()}
        # A transform whose trailing rank barely moves has no threshold to
        # apply. The per-cell check below catches it: a cell is marked
        # degenerate when the 20th and the 80th cut flag the same bars.
        ranks = {t: rolling_rank(v) for t, v in lagged.items()}
        for threshold in THRESHOLDS:
            direction = "below" if threshold <= 20 else "above"
            signals = {}
            for t, rank in ranks.items():
                flag = np.where(np.isnan(rank), -1,
                                (rank >= threshold).astype(int) if direction == "above"
                                else (rank <= threshold).astype(int))
                signals[t] = flag
            for target in TARGETS:
                horizon = int(target.split("_")[1])
                relative = target.startswith("rel_")
                for universe in UNIVERSES:
                    cid = cell_id(measure, transform_name, direction, threshold,
                                  target, universe)
                    if cid in done:
                        continue
                    names = (["BTC"] if universe == "btc" else
                             ["ETH"] if universe == "eth" else
                             [t for t in MAJORS if t in signals])
                    parts = []
                    for token in names:
                        got = score_signal(signals[token], forward(token, horizon, relative),
                                           horizon, years[token])
                        if got:
                            parts.append(got)
                    if not parts:
                        continue
                    n_ind = int(sum(p["n_independent"] for p in parts))
                    own = float(np.nanmean([p["spread_independent"] for p in parts]))
                    # A threshold that does not change who is flagged is not a
                    # threshold. pi_cycle fires once, so its raw rank sits above
                    # 98 for the whole window and every cut selects the same bars.
                    share = lambda cut: np.nanmean(np.where(
                        np.isnan(ranks[names[0]]), np.nan,
                        (ranks[names[0]] >= cut).astype(float) if direction == "above"
                        else (ranks[names[0]] <= cut).astype(float)))
                    extreme_share = share(80 if direction == "above" else 20)
                    degenerate = abs(share(20) - share(80)) < 0.01 or extreme_share > 0.5
                    neighbour_signs = []
                    for cut in NEIGHBOURS[threshold]:
                        alt = np.where(np.isnan(ranks[names[0]]), -1,
                                       (ranks[names[0]] >= cut).astype(int) if direction == "above"
                                       else (ranks[names[0]] <= cut).astype(int))
                        got = spread_only(alt, forward(names[0], horizon, relative), horizon)
                        if not np.isnan(got):
                            neighbour_signs.append(np.sign(got))
                    if names[0] != "BTC":
                        corr = {factor: np.nan for factor in admitted}
                    else:
                        corr = {}
                        sig0 = signals["BTC"].astype(float)
                        sig0[sig0 < 0] = np.nan
                        for factor, series in admitted.items():
                            both = ~np.isnan(sig0) & ~np.isnan(series)
                            corr[factor] = (float(np.corrcoef(sig0[both], series[both])[0, 1])
                                            if both.sum() > 30 else np.nan)
                    rows.append({
                        "id": cid, "measure": measure, "transform": transform_name,
                        "direction": direction, "threshold": int(threshold),
                        "target": target, "universe": universe,
                        "conditioning": "none", "timeframe": "daily",
                        "spread": float(np.nanmean([p["spread"] for p in parts])),
                        "spread_independent": own,
                        "t_newey_west": float(np.nanmean([p["t_newey_west"] for p in parts])),
                        "n_independent": n_ind,
                        "n_overlap": int(sum(p["n_overlap"] for p in parts)),
                        "below_minimum": bool(n_ind < MIN_INDEPENDENT),
                        "degenerate": bool(degenerate),
                        "fragile": bool(neighbour_signs and any(
                            s != np.sign(own) and s != 0 for s in neighbour_signs)),
                        "duplicate": bool(any(abs(v) > DUPLICATE_CORR
                                              for v in corr.values() if not np.isnan(v))),
                        "admitted_corr": json.dumps(corr),
                        "year_signs": json.dumps(parts[0]["year_signs"]),
                        "train_period_hash": period_hash,
                        "library_version": LIBRARY_VERSION,
                    })
    return rows
