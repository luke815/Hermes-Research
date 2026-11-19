"""One scoring harness for every hypothesis, so no test invents its own statistics.

Data: data/daily.pkl, a daily frame from the public dashboard file (BTC, ETH, 18 alts;
funding, OI, liquidations, long/short ratio; BTC/ETH options and basis), 2020-01-21 to 2026-11-17.

Rules fixed before any test is run (see PREREG.md):
  periods   train  <= 2024-06-30 | validation 2024-07-01..2025-12-31 | test >= 2026-01-01
  signal    computed from data up to and including day t (rolling windows only); the
            position is taken at the close of day t and held h days: r = c[t+h]/c[t]-1.
            A robustness run with lag=1 (take the position at t+1) is reported too.
  stats     spread = mean forward return on flagged days minus on unflagged days, with a
            Newey-West t (lag = h) from a regression on the flag. n_ind = number of flagged
            clusters more than h days apart (independent episodes).
  costs     round trip per trade: 10 bps BTC/ETH, 30 bps alts (taker 5 / 15 bps a side),
            charged on every flagged day. carry = funding over the hold, signed by side
            (funding columns are percent per 8h in the file; funding() converts to a fraction).
            net = gross - cost - carry.
  cross-section (18 alts): rank the signal across coins each day, long the top k short
            the bottom k (k=4), equal weight, h-day forward returns, spread per day,
            Newey-West t over days (lag h); costs 2 legs; carry by side.
  pass      same sign of spread in all three periods; validation |t_nw| >= 2 AND test
            spread same sign; n_ind >= 30 across train+validation; validation net > 0.
            Anything else is "insufficient" or "rejected", never "admitted".
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "daily.pkl")
RESULTS = os.path.join(HERE, "results")
PERIODS = {"train": (None, "2024-06-30"), "validation": ("2024-07-01", "2025-12-31"), "test": ("2026-01-01", None)}
COST_RT = {"btc": 0.0010, "eth": 0.0010, "alt": 0.0030}
ALTS = ["ADA", "APT", "ARB", "ATOM", "AVAX", "BCH", "BNB", "DOGE", "DOT", "FIL", "LINK", "LTC", "NEAR", "OP", "SOL", "SUI", "UNI", "XRP"]


def load():
    return pd.read_pickle(DATA)


def price(df, asset):
    return df["btc"] if asset == "btc" else df["eth"] if asset == "eth" else df[f"price_{asset}"]


def funding(df, asset):
    """Funding as a FRACTION per 8h settlement. The file stores percent per 8h (Binance default 0.01 = 1 bp)."""
    key = {"btc": "btc_funding", "eth": "eth_funding"}.get(asset, f"funding_{asset}")
    return df[key] / 100 if key in df else pd.Series(np.nan, index=df.index)


# ---------- transforms: rolling, past-only ----------
def _pct_window(w):
    x = w[-1]
    if np.isnan(x):
        return np.nan  # a missing day has no percentile; it must not read as "lowest ever"
    past = w[:-1]
    past = past[~np.isnan(past)]
    return (past <= x).mean() if len(past) else np.nan


def pct_rank(s, window=365, min_periods=180):
    """Where today sits in its trailing window, 0..1. Uses only data up to t; NaN days stay NaN.

    Fixed 2026-11-18: the first version compared the window against a NaN current value, which
    returned 0.0 and fired a false "bottom" flag on every gap day of a gappy series.
    """
    return s.rolling(window, min_periods=min_periods).apply(_pct_window, raw=True)


def zscore(s, window=90, min_periods=60):
    return (s - s.rolling(window, min_periods=min_periods).mean()) / s.rolling(window, min_periods=min_periods).std()


def change(s, k):
    return s - s.shift(k)


def pct_change(s, k):
    return s / s.shift(k) - 1


TRANSFORMS = {
    "raw": lambda s: s,
    "pct365": lambda s: pct_rank(s, 365, 180),
    "pct180": lambda s: pct_rank(s, 180, 90),
    "z90": lambda s: zscore(s, 90, 60),
    "z30": lambda s: zscore(s, 30, 20),
    "chg7": lambda s: change(s, 7),
    "chg30": lambda s: change(s, 30),
    "pchg7": lambda s: pct_change(s, 7),
    "pchg30": lambda s: pct_change(s, 30),
}


# ---------- statistics ----------
def nw_t(y, x, lag):
    """Newey-West t for the slope of y on x (x is the 0/1 flag or a standardized signal)."""
    m = ~(np.isnan(y) | np.isnan(x))
    y, x = y[m], x[m]
    n = len(y)
    if n < 10 or x.std() == 0:
        return np.nan, n
    X = np.column_stack([np.ones(n), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ beta
    XtX_inv = np.linalg.inv(X.T @ X)
    S = (X * e[:, None]).T @ (X * e[:, None])
    for l in range(1, lag + 1):
        w = 1 - l / (lag + 1)
        G = (X[l:] * e[l:, None]).T @ (X[:-l] * e[:-l, None])
        S += w * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    se = np.sqrt(max(V[1, 1], 1e-18))
    return float(beta[1] / se), n


def clusters(flag_index, h):
    """Number of flagged episodes more than h days apart."""
    if len(flag_index) == 0:
        return 0
    days = np.array(sorted(flag_index))
    gaps = np.diff(days).astype("timedelta64[D]").astype(int) if len(days) > 1 else np.array([])
    return 1 + int((gaps > h).sum())


def slice_period(s, name):
    lo, hi = PERIODS[name]
    out = s
    if lo:
        out = out[out.index >= lo]
    if hi:
        out = out[out.index <= hi]
    return out


# ---------- single-asset event test ----------
def event_test(df, series, transform, side, threshold, asset, horizons=(1, 3, 5, 10), lag=0, carry=True):
    """Flag days where transform(series) is >= threshold (side='top') or <= threshold (side='bottom').

    Returns a dict with per-horizon, per-period statistics and an overall verdict.
    """
    sig = TRANSFORMS[transform](df[series]).shift(lag)
    px = price(df, asset)
    fund = funding(df, asset)
    cost = COST_RT["btc" if asset == "btc" else "eth" if asset == "eth" else "alt"]
    flag = (sig >= threshold) if side == "top" else (sig <= threshold)
    flag = flag & sig.notna()
    out = {"series": series, "transform": transform, "side": side, "threshold": threshold, "asset": asset, "lag": lag,
           "horizons": {}}
    for h in horizons:
        fwd = px.shift(-h) / px - 1
        # carry for a long over the hold: funding rate (per 8h, as a fraction) paid 3x a day
        hold_carry = fund.rolling(h).sum().shift(-h) * 3 if carry else 0 * fwd
        rows = {}
        for pname in PERIODS:
            f, y, c = slice_period(flag, pname), slice_period(fwd, pname), slice_period(hold_carry, pname)
            m = y.notna() & f.notna()
            f, y, c = f[m], y[m], c[m]
            if f.sum() == 0 or (~f).sum() == 0:
                rows[pname] = {"n_flag": int(f.sum()), "n_ind": 0, "spread": None, "t_nw": None}
                continue
            spread = float(y[f].mean() - y[~f].mean())
            t, n = nw_t(y.to_numpy(float), f.to_numpy(float), h)
            long_side = spread > 0
            carry_cost = float(c[f].fillna(0).mean()) * (1 if long_side else -1)
            rows[pname] = {"n_flag": int(f.sum()), "n_ind": clusters(y[f].index, h), "n_days": int(m.sum()),
                           "mean_flag": float(y[f].mean()), "mean_rest": float(y[~f].mean()), "spread": spread,
                           "hit": float((y[f] > 0).mean()), "t_nw": t,
                           "net": spread - cost - carry_cost if long_side else -(spread) - cost - carry_cost,
                           "carry": carry_cost}
        out["horizons"][h] = rows
        out["horizons"][h]["verdict"] = verdict(rows)
    return out


def verdict(rows):
    tr, va, te = rows.get("train", {}), rows.get("validation", {}), rows.get("test", {})
    spreads = [r.get("spread") for r in (tr, va, te)]
    if any(s is None for s in spreads):
        return "insufficient: a period has no flagged or no unflagged days"
    n_ind = (tr.get("n_ind", 0) or 0) + (va.get("n_ind", 0) or 0)
    if n_ind < 30:
        return f"insufficient: {n_ind} independent episodes in train+validation (bar 30)"
    same = len({np.sign(s) for s in spreads}) == 1
    if not same:
        return "rejected: sign differs across periods"
    tv = va.get("t_nw")
    if tv is None or abs(tv) < 2:
        return f"rejected: validation t {tv if tv is None else round(tv, 2)} below 2"
    if va.get("net", 0) <= 0:
        return "rejected: validation net <= 0 after costs and carry"
    return "PASS: same sign in all periods, validation |t|>=2, net>0; confirm on the full universe before use"


# ---------- cross-sectional test over the 18 alts ----------
def cross_section_test(df, signal_fn, name, horizons=(1, 3, 5), k=4, lag=0, direction=1):
    """signal_fn(df, coin) -> Series. Long top k by signal, short bottom k, each day. direction=-1 flips.

    Returns per-horizon per-period: mean daily spread, NW t over days, IC (Spearman) mean and t, net after costs+carry.
    """
    sig = pd.DataFrame({c: signal_fn(df, c).shift(lag) for c in ALTS}) * direction
    px = pd.DataFrame({c: price(df, c) for c in ALTS})
    fund = pd.DataFrame({c: funding(df, c) for c in ALTS})
    out = {"name": name, "k": k, "lag": lag, "direction": direction, "horizons": {}}
    for h in horizons:
        fwd = px.shift(-h) / px - 1
        carry_h = fund.rolling(h).sum().shift(-h) * 3
        ranks = sig.rank(axis=1)
        nvalid = sig.notna().sum(axis=1)
        top = ranks.ge(nvalid.sub(k - 1), axis=0) & sig.notna()
        bot = ranks.le(k) & sig.notna()
        ok = (nvalid >= 2 * k + 2)
        long_r = fwd.where(top).mean(axis=1)
        short_r = fwd.where(bot).mean(axis=1)
        spread = (long_r - short_r).where(ok)
        carry = (carry_h.where(top).mean(axis=1) - carry_h.where(bot).mean(axis=1)).where(ok)
        ic = rank_ic(sig, fwd).where(ok)
        rows = {}
        for pname in PERIODS:
            sp = slice_period(spread, pname).dropna()
            cr = slice_period(carry, pname).reindex(sp.index).fillna(0)
            icp = slice_period(ic, pname).dropna()
            if len(sp) < 20:
                rows[pname] = {"n_days": int(len(sp)), "spread": None, "t_nw": None}
                continue
            t = nw_mean_t(sp.to_numpy(float), h)
            tic = nw_mean_t(icp.to_numpy(float), h) if len(icp) >= 20 else np.nan
            gross = float(sp.mean())
            cost = 2 * COST_RT["alt"] / h  # two legs, per day of holding
            rows[pname] = {"n_days": int(len(sp)), "n_ind": int(len(sp) // h), "spread": gross, "t_nw": float(t),
                           "ic": float(icp.mean()) if len(icp) else None, "ic_t": float(tic),
                           "carry": float(cr.mean()), "net": gross - cost - float(cr.mean()),
                           "hit": float((sp > 0).mean())}
        out["horizons"][h] = rows
        out["horizons"][h]["verdict"] = verdict({p: {**r, "n_ind": r.get("n_ind", 0)} for p, r in rows.items()})
    return out


def rank_ic(sig, fwd):
    """Per-day Spearman correlation across coins between signal and forward return, without scipy."""
    both = sig.notna() & fwd.notna()
    rs = sig.where(both).rank(axis=1)
    rf = fwd.where(both).rank(axis=1)
    rs = rs.sub(rs.mean(axis=1), axis=0)
    rf = rf.sub(rf.mean(axis=1), axis=0)
    num = (rs * rf).sum(axis=1)
    den = np.sqrt((rs ** 2).sum(axis=1) * (rf ** 2).sum(axis=1))
    out = num / den.replace(0, np.nan)
    return out.where(both.sum(axis=1) >= 6)


def nw_mean_t(x, lag):
    """Newey-West t of a mean (regression on a constant)."""
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 10:
        return np.nan
    e = x - x.mean()
    s = float((e * e).sum())
    for l in range(1, lag + 1):
        w = 1 - l / (lag + 1)
        s += 2 * w * float((e[l:] * e[:-l]).sum())
    se = np.sqrt(max(s, 1e-18)) / n
    return float(x.mean() / se)


# ---------- recording ----------
def save(name, payload):
    os.makedirs(RESULTS, exist_ok=True)
    payload = {"name": name, "written_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **payload}
    path = os.path.join(RESULTS, f"{name}.json")

    def clean(v):
        if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
            return None
        if isinstance(v, dict):
            return {str(k): clean(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [clean(x) for x in v]
        if isinstance(v, (np.floating, np.integer)):
            return clean(float(v))
        return v

    with open(path, "w") as handle:
        json.dump(clean(payload), handle, indent=1)
    return path


def summary_line(res):
    """One line per horizon: spread per period, t, n_ind, verdict."""
    lines = []
    for h, rows in res["horizons"].items():
        parts = []
        for p in ("train", "validation", "test"):
            r = rows.get(p, {})
            sp, t = r.get("spread"), r.get("t_nw")
            parts.append(f"{p[:3]} {sp * 100:+.2f}% t={t:.1f} n={r.get('n_ind', r.get('n_days', 0))}" if sp is not None and t is not None
                         else f"{p[:3]} -")
        lines.append(f"h={h}: " + " | ".join(parts) + f" -> {rows['verdict']}")
    return "\n".join(lines)


if __name__ == "__main__":
    df = load()
    demo = event_test(df, "btc_funding", "pct365", "top", 0.9, "btc")
    print(summary_line(demo))
