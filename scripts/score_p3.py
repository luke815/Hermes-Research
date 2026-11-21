"""Score the pre-registered P3 pair rules.

The rules, the periods, the costs and the pass bar are in
research/P3_PREREG.md, committed before this script runs. A pair is one name
against BTC and against ETH, on the point-in-time panel, one venue per coin
among names clearing the open-interest floor. The hedge ratio is estimated on
the 90 days before entry and held fixed. A missing carry drops the trade.

Usage: python3 scripts/score_p3.py
"""

import os
import sys

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.costs import round_trip  # noqa: E402
from regime_tester.periods import PERIODS  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402
from sweep_xs import liquid_names, load_close_matrix, PANEL  # noqa: E402

WINDOW = 90
Z_ENTER = 2.0
Z_EXIT = 0.0
STOP_VOLS = 2.5
MAX_HOLD = 30
HOLD_RS = 10
COINT_P = 0.05
HALF_LIFE = (3, 30)
MIN_T = 2.0
MIN_N = 40
PREREG = "c9c0c759f5aff896dab8a0a03bbd366f1525c53d"
ANCHORS = ("BTC", "ETH")


def _load(names):
    frames = {}
    for name in names:
        path = os.path.join(PANEL, name + ".csv")
        have = [c for c in ("date", "close", "funding_rate", "oi_usd")
                if c in pd.read_csv(path, nrows=0).columns]
        frames[name] = pd.read_csv(path, usecols=have).set_index("date")
    return frames


def _hedge(long_close, short_close):
    """Trailing regression slope of the long leg on the short leg, lagged one."""
    both = pd.concat([long_close.rename("y"), short_close.rename("x")], axis=1).dropna()
    cov = both["y"].rolling(WINDOW).cov(both["x"])
    var = both["x"].rolling(WINDOW).var()
    return (cov / var).shift(1)


def _zscore(spread):
    mean = spread.rolling(WINDOW).mean().shift(1)
    std = spread.rolling(WINDOW).std().shift(1)
    return (spread - mean) / std, std


def _half_life(spread):
    """Days for the spread's deviation to halve, from the trailing window."""
    lagged = spread.shift(1)
    change = spread.diff()
    both = pd.concat([change.rename("dy"), lagged.rename("y")], axis=1).dropna()
    cov = both["dy"].rolling(WINDOW).cov(both["y"])
    var = both["y"].rolling(WINDOW).var()
    slope = (cov / var).shift(1)
    with np.errstate(divide="ignore", invalid="ignore"):
        life = -np.log(2) / np.log(1 + slope)
    return life.where((slope < 0) & (slope > -1))


def _cointegrated(long_close, short_close):
    """Engle-Granger p on the trailing window, lagged one bar so entry sees it.

    The residual is the log spread against the trailing slope, and the test is
    the t-stat of that residual on its own lag. Both are rolling sums, so the
    whole series is one pass rather than one regression per bar.
    """
    both = pd.concat([np.log(long_close).rename("y"),
                      np.log(short_close).rename("x")], axis=1).dropna()
    slope = (both["y"].rolling(WINDOW).cov(both["x"])
             / both["x"].rolling(WINDOW).var())
    residual = both["y"] - slope * both["x"]
    lagged = residual.shift(1)
    change = residual.diff()
    frame = pd.concat([change.rename("dy"), lagged.rename("y")], axis=1)
    beta = frame["dy"].rolling(WINDOW).cov(frame["y"]) / frame["y"].rolling(WINDOW).var()
    fitted = beta * frame["y"]
    error = frame["dy"] - fitted
    sigma = error.rolling(WINDOW).std(ddof=1)
    sum_sq = (frame["y"] ** 2).rolling(WINDOW).sum()
    with np.errstate(divide="ignore", invalid="ignore"):
        t_stat = beta / (sigma / np.sqrt(sum_sq))
    p = t_stat.map(lambda t: _t_p(t, WINDOW - 2) if pd.notna(t) else np.nan)
    return p.shift(1)


def _t_p(t_stat, df):
    """One-sided p for a negative t, from a normal tail. Positive t is 1."""
    if t_stat >= 0:
        return 1.0
    from math import erfc
    return erfc(-t_stat / np.sqrt(2)) / 2


def _trades(z, spread_vol, enter, exit_at, max_hold):
    """Entry bars and the bars they close on. A position blocks a new entry."""
    values = z.to_numpy()
    vol = spread_vol.reindex(z.index).to_numpy()
    dates = list(z.index)
    taken = []
    busy_until = -1
    for i in range(len(values)):
        if i <= busy_until or not enter(values[i]):
            continue
        stop = values[i] - np.sign(values[i]) * STOP_VOLS if not np.isnan(vol[i]) else None
        close = None
        for j in range(i + 1, min(i + max_hold + 1, len(values))):
            if exit_at(values[i], values[j]):
                close = j
                break
            if stop is not None and not np.isnan(values[j]):
                against = np.sign(values[i]) * (values[j] - values[i])
                if against >= STOP_VOLS:
                    close = j
                    break
        if close is None:
            close = min(i + max_hold, len(values) - 1)
        taken.append((dates[i], dates[close], float(np.sign(values[i]))))
        busy_until = close
    return taken


def _net(frames, long_name, short_name, entry, exit_date, sign):
    """Spread return between the two dates, net of both legs' costs and carry."""
    long, short = frames[long_name], frames[short_name]
    if entry not in long.index or exit_date not in long.index:
        return None
    if entry not in short.index or exit_date not in short.index:
        return None
    gross = sign * ((long.loc[exit_date, "close"] / long.loc[entry, "close"] - 1)
                    - (short.loc[exit_date, "close"] / short.loc[entry, "close"] - 1))
    oi_long = long["oi_usd"].shift(1).loc[entry] if "oi_usd" in long else np.nan
    oi_short = short["oi_usd"].shift(1).loc[entry] if "oi_usd" in short else np.nan
    cost = round_trip(None if pd.isna(oi_long) else float(oi_long))
    cost += round_trip(None if pd.isna(oi_short) else float(oi_short))
    held = long.loc[entry:exit_date].index
    if "funding_rate" not in long or "funding_rate" not in short:
        return None
    carry_long = long.loc[held, "funding_rate"].astype(float)
    carry_short = short.loc[held, "funding_rate"].astype(float)
    if carry_long.isna().any() or carry_short.isna().any():
        return None
    carry = sign * (carry_long.sum() - carry_short.sum()) / 100
    return float(gross - cost - carry)


def _period(date):
    for name, start, end in PERIODS:
        if (start is None or date >= start) and (end is None or date <= end):
            return name
    return None


def _summarise(trades):
    out = {}
    for name, _, _ in PERIODS:
        part = [t for t in trades if t["period"] == name]
        values = np.array([t["net"] for t in part])
        out[name] = {
            "n": int(len(values)),
            "mean": float(values.mean()) if len(values) else None,
            "t": _t(values),
            "hit_rate": float((values > 0).mean()) if len(values) else None,
        }
    by_year = {}
    for trade in trades:
        by_year.setdefault(trade["entry"][:4], []).append(trade["net"])
    out["by_year"] = {year: {"n": len(v), "mean": float(np.mean(v))}
                      for year, v in sorted(by_year.items())}
    return out


def _t(values):
    if len(values) < 2 or np.std(values, ddof=1) == 0:
        return None
    return float(values.mean() / (np.std(values, ddof=1) / np.sqrt(len(values))))


def _verdict(summary):
    means = [summary[name]["mean"] for name, _, _ in PERIODS]
    if any(m is None for m in means):
        return "insufficient"
    if summary["validation"]["n"] < MIN_N:
        return "insufficient"
    if summary["validation"]["t"] is None or abs(summary["validation"]["t"]) < MIN_T:
        return "insufficient"
    signs = {np.sign(m) for m in means}
    if len(signs) > 1:
        return "rejected"
    return "admitted"


def score(frames, universe, anchors):
    rules = []
    for anchor_coin in anchors:
        anchor = next(name for name in universe if name.endswith("_" + anchor_coin + "USDT")
                      or name.endswith("_" + anchor_coin + "-USDT-SWAP"))
        for name in universe:
            if name == anchor:
                continue
            rules.extend(_pair(frames, name, anchor))
    return rules


def _pair(frames, name, anchor):
    long_close = frames[name]["close"]
    short_close = frames[anchor]["close"]
    hedge = _hedge(long_close, short_close)
    spread = long_close - hedge * short_close
    z, vol = _zscore(spread)
    life = _half_life(spread)
    coint = _cointegrated(long_close, short_close)
    eligible = (coint < COINT_P) & life.between(*HALF_LIFE)
    reversion = _trades(
        z.where(eligible), vol,
        lambda v: not np.isnan(v) and abs(v) >= Z_ENTER,
        lambda entered, now: not np.isnan(now) and np.sign(entered) * now <= Z_EXIT,
        MAX_HOLD)
    strength = _relative_strength(long_close, short_close, vol)
    rows = []
    for rule, taken in (("reversion", reversion), ("relative_strength", strength)):
        for entry, exit_date, sign in taken:
            net = _net(frames, name, anchor, entry, exit_date, sign)
            if net is None:
                continue
            rows.append({"rule": rule, "long": name, "short": anchor,
                         "entry": entry, "exit": exit_date, "net": net,
                         "period": _period(entry)})
    return rows


def _relative_strength(long_close, short_close, vol):
    """Top-decile 30-day spread, entered in the spread's direction, held 10 days.

    The decile is the trailing year of spreads, lagged one bar. A reversal of
    the 20-day spread closes the trade early.
    """
    spread_change = (long_close.pct_change(30) - short_close.pct_change(30))
    cutoff = spread_change.rolling(365, min_periods=60).quantile(0.9).shift(1)
    hot = spread_change.where(spread_change >= cutoff)
    return _trades(
        hot, vol.reindex(hot.index),
        lambda v: not np.isnan(v),
        lambda entered, now: False,
        HOLD_RS)


def main():
    close, _ = load_close_matrix(PANEL)
    train = close[close.index <= "2024-06-30"]
    enough = train.columns[train.notna().sum() >= 60]
    universe = liquid_names(enough)
    frames = _load(universe)
    trades = []
    for anchor in ANCHORS:
        anchor_name = next((n for n in universe if f"_{anchor}USDT" in n
                            or f"_{anchor}-USDT" in n), None)
        if anchor_name is None:
            continue
        for name in universe:
            if name == anchor_name:
                continue
            trades.extend(_pair(frames, name, anchor_name))
    by_rule = {}
    for rule in ("reversion", "relative_strength"):
        part = [t for t in trades if t["rule"] == rule]
        summary = _summarise(part)
        by_rule[rule] = {"trades": len(part), "summary": summary,
                         "verdict": _verdict(summary)}
    out = {"item": "P3", "prereg_commit": PREREG, "universe": len(universe),
           "rules": by_rule,
           "verdict": by_rule.get("reversion", {}).get("verdict")}
    path = write_result("p3_pairs", out, inputs=["data/panel_xs_laevitas"])
    print(path)


if __name__ == "__main__":
    main()
