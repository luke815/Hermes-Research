"""Pass-2 harness: conditioned events, excess (drift-controlled) spreads, daily or hourly bars.

Built on harness.py (same Newey-West t, same costs and carry, same periods for daily). Additions, all fixed in
PREREG2.md before scoring:

  frequency   "1d" (default) or "1h". Rolling windows are in bars (365 days or 90 days x 24 bars). Periods for 1h:
              train 2024-11-01..2025-06-30, validation 2025-07-01..2025-12-31, test 2026-01-01.. (exploratory).
  lag         bars between the signal bar and the entry bar. lag=1 is the primary specification in this pass.
  excess      spread is also measured against the SAME-PERIOD mean forward return (drift control); the verdict
              uses the excess spread, so a long-only rule in a bull run does not pass on drift alone.
  conditioned event_test2(..., cond=(series, transform, side, threshold)): the flag is primary AND conditioner.
              The result carries the parent (unconditioned) cell and the lift = conditioned spread - parent spread.
              verdict2 refuses a conditioned pass when the parent has the other sign in validation or the lift is
              not positive in both train and validation (that is interaction mining, not a signal).
  abs_target  for straddle-type hypotheses (butterfly), the target is |forward return| and the spread is in
              absolute-return terms; costs are charged twice (two legs).
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import harness as H  # noqa: E402

PERIODS_1H = {"train": ("2024-11-01", "2025-06-30"), "validation": ("2025-07-01", "2025-12-31"), "test": ("2026-01-01", None)}
BARS_PER_DAY = {"1d": 1, "1h": 24, "3d": 1 / 3, "4h": 6}  # 3d/4h added in pass 3 (TD Sequential)


def periods_for(freq):
    return H.PERIODS if freq in ("1d", "3d") else PERIODS_1H


def transform(series, name, freq="1d"):
    """Rolling, past-only transforms with windows in bars. pct365 means 365 days whatever the bar size."""
    b = BARS_PER_DAY[freq]
    table = {
        "raw": lambda s: s,
        "pct365": lambda s: H.pct_rank(s, int(365 * b), int(180 * b)),
        "pct180": lambda s: H.pct_rank(s, int(180 * b), int(90 * b)),
        "pct90": lambda s: H.pct_rank(s, int(90 * b), int(45 * b)),
        "z90": lambda s: H.zscore(s, int(90 * b), int(60 * b)),
        "z30": lambda s: H.zscore(s, int(30 * b), int(20 * b)),
        "chg1": lambda s: H.change(s, max(1, int(1 * b))),
        "chg4b": lambda s: H.change(s, 4),
        "chg5": lambda s: H.change(s, max(1, int(5 * b))),
        "chg7": lambda s: H.change(s, max(1, int(7 * b))),
        "pchg3": lambda s: H.pct_change(s, max(1, int(3 * b))),
        "pchg7": lambda s: H.pct_change(s, max(1, int(7 * b))),
        "pchg24b": lambda s: H.pct_change(s, 24),
    }
    return table[name](series)


def make_flag(df, spec, freq, lag):
    """spec = (series, transform, side, threshold) or a list of transforms applied in order, e.g.
    ("skew_30", ["chg1", "z30"], "top", 2)."""
    series, tr, side, thr = spec
    s = df[series]
    for name in ([tr] if isinstance(tr, str) else tr):
        s = transform(s, name, freq)
    s = s.shift(lag)
    flag = (s >= thr) if side == "top" else (s <= thr)
    return flag & s.notna(), s


def slice_period(s, name, freq):
    lo, hi = periods_for(freq)[name]
    out = s
    if lo:
        out = out[out.index >= lo]
    if hi:
        out = out[out.index <= hi]
    return out


def clusters(index, h, freq):
    """Independent episodes: flagged bars more than h bars apart."""
    if len(index) == 0:
        return 0
    pos = np.array(sorted(index))
    unit = {"1d": np.timedelta64(1, "D"), "3d": np.timedelta64(3, "D"), "1h": np.timedelta64(1, "h"), "4h": np.timedelta64(4, "h")}[freq]
    gaps = (np.diff(pos) / unit).astype(float) if len(pos) > 1 else np.array([])
    return 1 + int((gaps > h).sum())


def score_flag(flag, fwd, carry_h, cost, h, freq, abs_target=False, valid=None):
    """valid: bars where the signal itself is defined. The comparison set (all bars, unflagged bars, the period mean) is
    restricted to those bars, so a series that starts in 2021 is not measured against a 2019-2021 baseline it never saw.
    Fix of 2026-11-19 (pass-3 refutation found the old all-bars baseline inflated train 'excess' for late-starting series)."""
    rows = {}
    for pname in periods_for(freq):
        f, y, c = slice_period(flag, pname, freq), slice_period(fwd, pname, freq), slice_period(carry_h, pname, freq)
        m = y.notna() & f.notna()
        if valid is not None:
            m &= slice_period(valid, pname, freq).fillna(False).astype(bool)
        f, y, c = f[m], y[m], c[m]
        if f.sum() < 3 or (~f).sum() < 10:
            rows[pname] = {"n_flag": int(f.sum()), "n_ind": 0, "spread": None, "excess": None, "t_nw": None}
            continue
        target = y.abs() if abs_target else y
        spread = float(target[f].mean() - target[~f].mean())
        excess = float(target[f].mean() - target.mean())
        t, _ = H.nw_t(target.to_numpy(float), f.to_numpy(float), h)
        long_side = excess > 0
        carry_cost = float(c[f].fillna(0).mean()) * (1 if long_side else -1)
        legs = 2 if abs_target else 1
        net = (abs(excess) - cost * legs - carry_cost)
        rows[pname] = {"n_flag": int(f.sum()), "n_ind": clusters(y[f].index, h, freq), "n_bars": int(m.sum()),
                       "mean_flag": float(target[f].mean()), "mean_all": float(target.mean()), "spread": spread,
                       "excess": excess, "hit": float((y[f] > 0).mean()), "t_nw": t, "net": net, "carry": carry_cost}
    return rows


def verdict2(rows, parent=None, bar=2.5, episode_bar=30):
    tr, va, te = rows.get("train", {}), rows.get("validation", {}), rows.get("test", {})
    ex = [r.get("excess") for r in (tr, va, te)]
    if any(e is None for e in ex):
        return "insufficient: a period has fewer than 3 flagged bars"
    n_ind = (tr.get("n_ind") or 0) + (va.get("n_ind") or 0)
    if n_ind < episode_bar:
        return f"insufficient: {n_ind} independent episodes in train+validation (bar {episode_bar})"
    if len({np.sign(e) for e in ex}) != 1:
        return "rejected: excess sign differs across periods"
    tv = va.get("t_nw")
    if tv is None or abs(tv) < bar:
        return f"rejected: validation t {round(tv, 2) if tv is not None else None} below {bar}"
    if (va.get("net") or 0) <= 0:
        return "rejected: validation net <= 0 after costs and carry"
    if parent is not None:
        pv, pt = parent.get("validation", {}), parent.get("train", {})
        if pv.get("excess") is None or np.sign(pv["excess"]) != np.sign(va["excess"]):
            return "rejected as interaction mining: the unconditioned parent has the other sign in validation"
        lift_tr = (tr["excess"] - (pt.get("excess") or 0)) * np.sign(va["excess"])
        lift_va = (va["excess"] - pv["excess"]) * np.sign(va["excess"])
        if lift_tr <= 0 or lift_va <= 0:
            return f"rejected: conditioning adds nothing (lift train {lift_tr * 100:+.2f}%, validation {lift_va * 100:+.2f}%)"
    return "PASS: excess same sign in all periods, validation |t|>=2.5, net>0" + (", conditioned lift positive in train and validation" if parent else "") + "; candidate for confirmation, not a signal"


def event_test2(df, primary, asset, horizons=(1, 3, 5, 10, 20), freq="1d", lag=1, cond=None, abs_target=False, bar=2.5, episode_bar=30):
    """primary/cond = (series, transform(s), side, threshold). asset: 'btc' | 'eth' | an alt symbol.

    Returns per-horizon rows for the conditioned cell and, when cond is given, the parent cell and the lift.
    """
    px = H.price(df, asset)
    fund = H.funding(df, asset)
    cost = H.COST_RT["btc" if asset == "btc" else "eth" if asset == "eth" else "alt"]
    flag_p, sig_p = make_flag(df, primary, freq, lag)
    flag = flag_p
    valid = sig_p.notna()
    if cond is not None:
        flag_c, sig_c = make_flag(df, cond, freq, lag)
        flag = flag_p & flag_c
        valid = valid & sig_c.notna()
    out = {"primary": list(map(str, primary)), "cond": list(map(str, cond)) if cond else None, "asset": asset,
           "freq": freq, "lag": lag, "abs_target": abs_target, "baseline": "bars where the signal is defined", "horizons": {}}
    b = BARS_PER_DAY[freq]
    for h in horizons:
        fwd = px.shift(-h) / px - 1
        settlements = 3 * h / b  # 8h funding settlements during a hold of h bars
        carry_h = fund.rolling(h).mean().shift(-h) * settlements if freq == "1d" else fund.rolling(h).mean().shift(-h) * settlements
        rows = score_flag(flag, fwd, carry_h, cost, h, freq, abs_target, valid)
        parent = score_flag(flag_p, fwd, carry_h, cost, h, freq, abs_target, valid) if cond is not None else None
        entry = {"cell": rows}
        if parent is not None:
            entry["parent"] = parent
            entry["lift"] = {p: (rows[p]["excess"] - parent[p]["excess"]) if rows[p].get("excess") is not None and parent[p].get("excess") is not None else None
                             for p in rows}
        entry["verdict"] = verdict2(rows, parent, bar, episode_bar)
        out["horizons"][h] = entry
    return out


def line2(res):
    lines = []
    for h, e in res["horizons"].items():
        parts = []
        for p in ("train", "validation", "test"):
            r = e["cell"].get(p, {})
            if r.get("excess") is None:
                parts.append(f"{p[:3]} -")
                continue
            lift = f" lift {e['lift'][p] * 100:+.2f}" if "lift" in e and e["lift"].get(p) is not None else ""
            parts.append(f"{p[:3]} ex {r['excess'] * 100:+.2f}% t={r['t_nw']:.1f} n={r['n_ind']} net={r['net'] * 100:+.2f}%{lift}")
        lines.append(f"h={h}: " + " | ".join(parts) + f" -> {e['verdict']}")
    return "\n".join(lines)


if __name__ == "__main__":
    df = pd.read_pickle(os.path.join(HERE, "data", "daily2.pkl")) if os.path.exists(os.path.join(HERE, "data", "daily2.pkl")) else H.load()
    print(line2(event_test2(df, ("btc_funding", "pct365", "bottom", 0.1), "btc", horizons=(3, 5))))


# ---------- RISK targets: forward drawdown, crash probability, forward vol, missed upside ----------
def forward_mdd(px, W):
    """Worst close-to-close drawdown from t over the next W bars (<= 0)."""
    fwd_min = px[::-1].rolling(W, min_periods=1).min()[::-1].shift(-1)
    return (fwd_min / px - 1).where(px.shift(-W).notna())


def forward_rv(px, W, bars_per_day=1):
    r = np.log(px / px.shift(1))
    return (r[::-1].rolling(W).std()[::-1].shift(-1) * np.sqrt(365 * bars_per_day)).where(px.shift(-W).notna())


def auc(score, event):
    """Rank-based AUC of a continuous score for a binary event, without sklearn."""
    m = score.notna() & event.notna()
    s, e = score[m], event[m].astype(bool)
    if e.sum() < 5 or (~e).sum() < 5:
        return None
    ranks = s.rank()
    n1, n0 = int(e.sum()), int((~e).sum())
    return float((ranks[e].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def risk_test(df, primary, asset, windows=(10, 20, 30), freq="1d", lag=1, cond=None, crash=-0.10, episode_bar=20):
    """Score a flag against forward drawdown, crash probability, forward vol and missed upside."""
    px = H.price(df, asset)
    flag_p, sig = make_flag(df, primary, freq, lag)
    flag = flag_p
    valid = sig.notna()
    if cond is not None:
        flag_c, sig_c = make_flag(df, cond, freq, lag)
        flag = flag_p & flag_c
        valid = valid & sig_c.notna()
    out = {"primary": list(map(str, primary)), "cond": list(map(str, cond)) if cond else None, "asset": asset,
           "freq": freq, "lag": lag, "crash": crash, "baseline": "bars where the signal is defined", "windows": {}}
    b = BARS_PER_DAY[freq]
    fwd20 = px.shift(-max(1, int(round(20 * b)))) / px - 1
    for W in windows:
        Wb = max(1, int(round(W * b)))
        mdd = forward_mdd(px, Wb)
        rv = forward_rv(px, Wb, b)
        rows = {}
        for pname in periods_for(freq):
            f, d, v, r20, s = (slice_period(x, pname, freq) for x in (flag, mdd, rv, fwd20, sig))
            m = d.notna() & f.notna() & slice_period(valid, pname, freq).fillna(False).astype(bool)
            f, d, v, r20, s = f[m], d[m], v[m], r20[m], s[m]
            if f.sum() < 3:
                rows[pname] = {"n_flag": int(f.sum()), "n_ind": 0, "mdd_diff": None}
                continue
            ev = d <= crash
            t, _ = H.nw_t(d.to_numpy(float), f.to_numpy(float), Wb)
            base = float(ev.mean()) if len(ev) else None
            cond_rate = float(ev[f].mean())
            rows[pname] = {
                "n_flag": int(f.sum()), "n_ind": clusters(d[f].index, Wb, freq), "n_bars": int(m.sum()),
                "mdd_flag": float(d[f].mean()), "mdd_all": float(d.mean()), "mdd_diff": float(d[f].mean() - d.mean()),
                "t_nw": t,
                "crash_rate_flag": cond_rate, "crash_rate_all": base,
                "crash_lift": (cond_rate / base) if base else None,
                "crash_n": int(ev[f].sum()),
                "auc": auc(s * (1 if primary[2] == "top" else -1), ev),
                "rv_flag": float(v[f].mean()) if v[f].notna().any() else None, "rv_all": float(v.mean()) if v.notna().any() else None,
                "q05_flag": float(r20[f].quantile(0.05)) if r20[f].notna().sum() >= 5 else None,
                "q05_all": float(r20.quantile(0.05)) if r20.notna().sum() >= 5 else None,
                "missed_mean20": float(r20[f].mean()) if r20[f].notna().any() else None,
                "false_alarm": float((r20[f] > 0).mean()) if r20[f].notna().any() else None,
            }
        out["windows"][W] = {"cell": rows, "verdict": risk_verdict(rows, W, episode_bar=episode_bar)}
    return out


def risk_verdict(rows, W, bar=2.5, episode_bar=20):
    tr, va, te = rows.get("train", {}), rows.get("validation", {}), rows.get("test", {})
    diffs = [r.get("mdd_diff") for r in (tr, va, te)]
    if any(x is None for x in diffs):
        return "insufficient: a period has fewer than 3 flagged bars"
    n_ind = (tr.get("n_ind") or 0) + (va.get("n_ind") or 0)
    if n_ind < episode_bar:
        return f"insufficient: {n_ind} independent episodes in train+validation (bar {episode_bar})"
    signs = {np.sign(x) for x in diffs}
    if len(signs) != 1:
        return "rejected: drawdown effect changes sign across periods"
    tv = va.get("t_nw")
    if tv is None or abs(tv) < bar:
        return f"rejected: validation t {round(tv, 2) if tv is not None else None} on mdd below {bar}"
    lv, lt = va.get("crash_lift"), te.get("crash_lift")
    if diffs[1] < 0:  # risk-off candidate: deeper drawdowns ahead
        if lv is None or lv < 1.5 or lt is None or lt < 1.2:
            return f"rejected (risk-off): crash lift validation {lv and round(lv, 2)}, test {lt and round(lt, 2)} below 1.5 / 1.2"
        if (va.get("false_alarm") or 0) >= 0.6:
            return f"rejected (risk-off): false-alarm rate {round(va['false_alarm'], 2)}: most flagged periods still ended higher"
        return "PASS risk-off: deeper drawdowns in all periods, validation |t|>=2.5, crash lift holds, false alarms < 60%; candidate for the dial"
    if lv is None or lv > 0.6 or lt is None or lt > 0.8 or (va.get("missed_mean20") or 0) <= 0:
        return f"rejected (risk-on): crash lift validation {lv and round(lv, 2)}, test {lt and round(lt, 2)} not low enough, or 20d mean not positive"
    return "PASS risk-on: shallower drawdowns in all periods, validation |t|>=2.5, crash lift low; candidate for the dial"


def risk_line(res):
    lines = []
    for W, e in res["windows"].items():
        parts = []
        for p in ("train", "validation", "test"):
            r = e["cell"].get(p, {})
            if r.get("mdd_diff") is None:
                parts.append(f"{p[:3]} -")
                continue
            parts.append(f"{p[:3]} mdd {r['mdd_diff'] * 100:+.1f}% t={r['t_nw']:.1f} crash x{(r['crash_lift'] or 0):.2f} "
                         f"({r['crash_n']}/{r['n_flag']}) fa={r['false_alarm']:.2f} n={r['n_ind']}")
        lines.append(f"W={W}: " + " | ".join(parts) + f" -> {e['verdict']}")
    return "\n".join(lines)
