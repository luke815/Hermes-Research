"""Pass-3 additions: TD Sequential, regime duration and exit flags, resampling to 3D and 4H.

All past-only. Used with harness2.event_test2 / risk_test through plain df columns, so the same
periods, costs, carry, excess spreads, drawdown targets and verdict rules apply.

TD Sequential (DeMark), standard definitions:
  buy setup   : 9 consecutive bars with close < close[4 bars earlier]; completes on the 9th bar
  sell setup  : 9 consecutive bars with close > close[4 bars earlier]
  perfected   : buy setup where low of bar 8 or 9 <= low of bars 6 and 7 (mirror for sell with highs)
  buy countdown: after a completed buy setup, count bars with close <= low[2 bars earlier]; 13 completes
  sell countdown: after a completed sell setup, bars with close >= high[2 bars earlier]; 13 completes
  Countdown is cancelled by a completed opposite setup.
Columns produced by td_columns(df, "btc"): td_buy9_btc, td_sell9_btc (1 on the completion bar),
td_buy9p_btc, td_sell9p_btc (perfected), td_buy13_btc, td_sell13_btc (countdown completion), td_setup_btc
(signed count, +n sell / -n buy, informational).

Regime duration: days_in_state(flag) = consecutive bars the flag has been true, 0 otherwise.
Exit event: exit_after(flag, min_run) = 1 on the first bar the flag is false after >= min_run consecutive
true bars.

Resampling: to_3d(df) takes every third daily bar's close (close of a 3-day window, non-overlapping,
anchored at the first date); to_4h(hourly) takes the close every 4 hours from a 1h frame. Funding and
other series are sampled at the same bars.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import harness as H  # noqa: E402
import harness2 as H2  # noqa: E402


def td_sequential(close, high=None, low=None):
    """TD setup and countdown flags from a close series (highs/lows optional for perfection and countdown)."""
    c = close.to_numpy(float)
    n = len(c)
    hi = (high if high is not None else close).to_numpy(float)
    lo = (low if low is not None else close).to_numpy(float)
    setup = np.zeros(n)         # +k sell setup count, -k buy setup count
    buy9 = np.zeros(n); sell9 = np.zeros(n); buy9p = np.zeros(n); sell9p = np.zeros(n)
    buy13 = np.zeros(n); sell13 = np.zeros(n)
    b_count = s_count = 0
    cd_buy = None; cd_sell = None  # countdown counters, None when inactive
    for i in range(n):
        if i < 4 or np.isnan(c[i]) or np.isnan(c[i - 4]):
            b_count = s_count = 0
            continue
        if c[i] < c[i - 4]:
            b_count += 1; s_count = 0
        elif c[i] > c[i - 4]:
            s_count += 1; b_count = 0
        else:
            b_count = s_count = 0
        setup[i] = s_count if s_count else -b_count
        if b_count == 9:
            buy9[i] = 1
            if i >= 8 and (min(lo[i], lo[i - 1]) <= min(lo[i - 2], lo[i - 3])):
                buy9p[i] = 1
            cd_buy = 0; cd_sell = None
        if s_count == 9:
            sell9[i] = 1
            if i >= 8 and (max(hi[i], hi[i - 1]) >= max(hi[i - 2], hi[i - 3])):
                sell9p[i] = 1
            cd_sell = 0; cd_buy = None
        if cd_buy is not None and i >= 2 and not np.isnan(lo[i - 2]) and c[i] <= lo[i - 2]:
            cd_buy += 1
            if cd_buy == 13:
                buy13[i] = 1; cd_buy = None
        if cd_sell is not None and i >= 2 and not np.isnan(hi[i - 2]) and c[i] >= hi[i - 2]:
            cd_sell += 1
            if cd_sell == 13:
                sell13[i] = 1; cd_sell = None
    idx = close.index
    return pd.DataFrame({"setup": setup, "buy9": buy9, "sell9": sell9, "buy9p": buy9p, "sell9p": sell9p,
                         "buy13": buy13, "sell13": sell13}, index=idx)


def td_columns(df, asset, close_col=None, high_col=None, low_col=None):
    close = df[close_col] if close_col else H.price(df, asset)
    high = df[high_col] if high_col and high_col in df else None
    low = df[low_col] if low_col and low_col in df else None
    td = td_sequential(close, high, low)
    for k in td.columns:
        df[f"td_{k}_{asset}"] = td[k]
    return df


def days_in_state(flag):
    """Consecutive true bars up to and including t; 0 when false."""
    f = flag.fillna(False).astype(bool).to_numpy()
    out = np.zeros(len(f))
    run = 0
    for i, v in enumerate(f):
        run = run + 1 if v else 0
        out[i] = run
    return pd.Series(out, index=flag.index)


def exit_after(flag, min_run):
    """1 on the first bar the flag is false after at least min_run consecutive true bars."""
    runs = days_in_state(flag)
    prev = runs.shift(1).fillna(0)
    f = flag.fillna(False).astype(bool)
    return ((~f) & (prev >= min_run)).astype(float)


def state_columns(df, series, asset_tag, pct_window=365, hi=0.8, lo=0.2):
    """Adds <series>_hi_run, <series>_hi_exit20, <series>_hi_exit40, <series>_lo_run, <series>_lo_exit20."""
    p = H.pct_rank(df[series], pct_window, pct_window // 2)
    hiflag, loflag = p >= hi, p <= lo
    df[f"{series}_hi_run"] = days_in_state(hiflag)
    df[f"{series}_lo_run"] = days_in_state(loflag)
    for m in (20, 40):
        df[f"{series}_hi_exit{m}"] = exit_after(hiflag, m)
        df[f"{series}_lo_exit{m}"] = exit_after(loflag, m)
    return df


def to_3d(df):
    """Every third daily bar; the close is that bar's close. Funding stays per-8h and is summed by the harness."""
    out = df.iloc[::3].copy()
    return out


def to_4h(hourly):
    """Every fourth hourly bar from a 1h frame (closes at 00,04,08,...). Funding per-8h columns are kept."""
    return hourly[hourly.index.hour % 4 == 0].copy()


if __name__ == "__main__":
    d = pd.read_pickle(os.path.join(HERE, "data", "daily2.pkl"))
    td_columns(d, "btc")
    print("daily TD9 buy completions:", int(d["td_buy9_btc"].sum()), "sell:", int(d["td_sell9_btc"].sum()),
          "buy13:", int(d["td_buy13_btc"].sum()), "sell13:", int(d["td_sell13_btc"].sum()))
    state_columns(d, "perp_funding_btc", "btc")
    print("funding hi-state exits after 20d:", int(d["perp_funding_btc_hi_exit20"].sum()), "after 40d:", int(d["perp_funding_btc_hi_exit40"].sum()))
