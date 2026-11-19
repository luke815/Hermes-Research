"""Refutation of: BTC lsr_BTC top quintile/decile (pct365) -> below-average 30-90d returns, deeper drawdowns, all periods.

Writes results3/refute/lsr_btc_refute.json and prints a text log (captured to lsr_btc_refute.txt by the caller).
Nothing outside results3/refute/ is touched. Harness files are imported, not modified.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
import harness as H  # noqa: E402
import harness2 as H2  # noqa: E402

df = pd.read_pickle(os.path.join(ROOT, "data", "daily2.pkl"))
px = H.price(df, "btc")
OUT = {}
HORIZONS = (30, 60, 90)
WINDOWS = (30, 60, 90)
CRASH = {30: -0.10, 60: -0.20, 90: -0.20}


def P(*a):
    print(*a, flush=True)


def section(title):
    P("\n" + "=" * 100 + "\n" + title + "\n" + "=" * 100)


def per_period(s):
    return {p: H2.slice_period(s, p, "1d") for p in H.PERIODS}


def ret_rows(res):
    """Compact per-horizon rows from event_test2 output."""
    rows = {}
    for h, e in res["horizons"].items():
        rows[h] = {p: {k: e["cell"][p].get(k) for k in ("excess", "t_nw", "n_ind", "n_flag", "mean_flag", "mean_all")} for p in H.PERIODS}
    return rows


def risk_rows(res):
    rows = {}
    for W, e in res["windows"].items():
        rows[W] = {p: {k: e["cell"][p].get(k) for k in ("mdd_diff", "t_nw", "n_ind", "n_flag", "crash_lift", "crash_n", "false_alarm")} for p in H.PERIODS}
    return rows


def fmt_ret(rows):
    out = []
    for h, r in rows.items():
        parts = []
        for p in ("train", "validation", "test"):
            x = r[p]
            parts.append(f"{p[:3]} -" if x.get("excess") is None else f"{p[:3]} ex {x['excess']*100:+.1f}% t={x['t_nw']:.1f} n={x['n_ind']}")
        out.append(f"  h={h}: " + " | ".join(parts))
    return "\n".join(out)


def fmt_risk(rows):
    out = []
    for W, r in rows.items():
        parts = []
        for p in ("train", "validation", "test"):
            x = r[p]
            parts.append(f"{p[:3]} -" if x.get("mdd_diff") is None else f"{p[:3]} mdd {x['mdd_diff']*100:+.1f} t={x['t_nw']:.1f} lift x{(x['crash_lift'] or 0):.2f} n={x['n_ind']}")
        out.append(f"  W={W}: " + " | ".join(parts))
    return "\n".join(out)


def run_cell(thr, lag, cond=None, label=None):
    spec = ("lsr_BTC", "pct365", "top", thr)
    r = H2.event_test2(df, spec, "btc", horizons=HORIZONS, lag=lag, cond=cond, episode_bar=15)
    rr = ret_rows(r)
    risk = {}
    for W in WINDOWS:
        k = H2.risk_test(df, spec, "btc", windows=(W,), lag=lag, cond=cond, crash=CRASH[W], episode_bar=20)
        risk.update(risk_rows(k))
    label = label or f"thr={thr} lag={lag}" + (f" cond={cond}" if cond else "")
    P(f"[{label}]")
    P(fmt_ret(rr))
    P(fmt_risk(risk))
    return {"ret": rr, "risk": risk}


# ---------------------------------------------------------------------------------------------------------------
section("0. Baseline reproduction (lag=1, thr 0.8 / 0.9)")
OUT["baseline"] = {str(t): run_cell(t, 1) for t in (0.8, 0.9)}

# ---------------------------------------------------------------------------------------------------------------
section("1. lag=2 and lag=5")
OUT["lags"] = {}
for lag in (2, 5):
    for t in (0.8, 0.9):
        OUT["lags"][f"thr{t}_lag{lag}"] = run_cell(t, lag)

# ---------------------------------------------------------------------------------------------------------------
section("2. Threshold neighbours 0.7 / 0.75 / 0.85 / 0.95 (lag=1)")
OUT["thresholds"] = {}
for t in (0.7, 0.75, 0.85, 0.95):
    OUT["thresholds"][str(t)] = run_cell(t, 1)

# ---------------------------------------------------------------------------------------------------------------
section("3. Episode-level test: one observation per independent episode (first flagged day of each cluster > h apart)")


def episodes(flag, h):
    """First flagged date of each cluster where consecutive flagged dates are more than h days apart."""
    idx = flag[flag].index
    if len(idx) == 0:
        return []
    starts = [idx[0]]
    for a, b in zip(idx[:-1], idx[1:]):
        if (b - a).days > h:
            starts.append(b)
    return starts


def episode_table(thr, lag=1, target="ret"):
    flag, sig = H2.make_flag(df, ("lsr_BTC", "pct365", "top", thr), "1d", lag)
    res = {}
    for h in HORIZONS:
        fwd = px.shift(-h) / px - 1
        mdd = H2.forward_mdd(px, h)
        res[h] = {}
        for p in H.PERIODS:
            f = H2.slice_period(flag, p, "1d")
            y = H2.slice_period(fwd, p, "1d")
            d = H2.slice_period(mdd, p, "1d")
            m = y.notna()
            f = f[m]
            eps = episodes(f, h)
            ex = [float(y.loc[e] - y[m].mean()) for e in eps]
            dd = [float(d.loc[e] - d[m].mean()) for e in eps if not np.isnan(d.loc[e])]
            n = len(ex)
            neg = sum(1 for v in ex if v < 0)
            # exact two-sided binomial p (no scipy): P(X<=min(neg,n-neg)) * 2
            from math import comb
            k = min(neg, n - neg) if n else 0
            pbin = min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n) if n else None
            res[h][p] = {"n_episodes": n, "dates": [str(e.date()) for e in eps],
                         "excess_each": [round(v, 4) for v in ex],
                         "mean_excess": float(np.mean(ex)) if n else None,
                         "median_excess": float(np.median(ex)) if n else None,
                         "n_negative": neg, "sign_p_two_sided": pbin,
                         "mdd_diff_each": [round(v, 4) for v in dd],
                         "mean_mdd_diff": float(np.mean(dd)) if dd else None,
                         "n_mdd_deeper": sum(1 for v in dd if v < 0)}
    return res


OUT["episodes"] = {}
for t in (0.8, 0.9):
    tab = episode_table(t)
    OUT["episodes"][str(t)] = tab
    P(f"[thr={t} lag=1] one row per episode (cluster start), excess = fwd return at start minus period mean")
    for h in HORIZONS:
        for p in ("train", "validation", "test"):
            r = tab[h][p]
            P(f"  h={h} {p[:3]}: n_ep={r['n_episodes']} neg={r['n_negative']} sign_p={r['sign_p_two_sided'] if r['sign_p_two_sided'] is None else round(r['sign_p_two_sided'],3)} "
              f"mean_ex={'-' if r['mean_excess'] is None else f'{r['mean_excess']*100:+.1f}%'} med_ex={'-' if r['median_excess'] is None else f'{r['median_excess']*100:+.1f}%'} "
              f"mdd_deeper={r['n_mdd_deeper']}/{len(r['mdd_diff_each'])} mean_mdd_diff={'-' if r['mean_mdd_diff'] is None else f'{r['mean_mdd_diff']*100:+.1f}'}")
            P(f"     dates: {r['dates']}")
            P(f"     excess: {[round(v*100,1) for v in r['excess_each']]}")

# ---------------------------------------------------------------------------------------------------------------
section("4. Confound: lsr rises when price falls. Correlation of lsr pct with trailing 10/30d return; conditional tests; price-only control")
sig_pct = H2.transform(df["lsr_BTC"], "pct365")
r10 = px / px.shift(10) - 1
r30 = px / px.shift(30) - 1
r30_pct = H2.transform(r30, "pct365")
OUT["confound"] = {"corr": {}}
for p in H.PERIODS:
    sp = H2.slice_period(sig_pct, p, "1d")
    a = H2.slice_period(r10, p, "1d").reindex(sp.index)
    b = H2.slice_period(r30, p, "1d").reindex(sp.index)
    raw = H2.slice_period(df["lsr_BTC"], p, "1d").reindex(sp.index)
    m = sp.notna() & a.notna() & b.notna()
    c10 = float(np.corrcoef(sp[m], a[m])[0, 1]); c30 = float(np.corrcoef(sp[m], b[m])[0, 1])
    def spear(u, v):
        return float(np.corrcoef(u.rank().to_numpy(float), v.rank().to_numpy(float))[0, 1])
    s10 = spear(sp[m], a[m]); s30 = spear(sp[m], b[m])
    craw30 = spear(raw[m], b[m])
    # trailing 30d return of flagged days vs all
    flag8 = (sp >= 0.8) & sp.notna()
    flag9 = (sp >= 0.9) & sp.notna()
    OUT["confound"]["corr"][p] = {"pearson_pct_vs_r10": c10, "pearson_pct_vs_r30": c30, "spearman_pct_vs_r10": s10, "spearman_pct_vs_r30": s30,
                                  "spearman_rawlsr_vs_r30": craw30,
                                  "trailing_r30_mean_flag08": float(b[flag8 & m].mean()), "trailing_r30_mean_flag09": float(b[flag9 & m].mean()),
                                  "trailing_r30_mean_all": float(b[m].mean()),
                                  "share_flag08_with_neg_r30": float((b[flag8 & m] < 0).mean()) if (flag8 & m).sum() else None,
                                  "share_flag09_with_neg_r30": float((b[flag9 & m] < 0).mean()) if (flag9 & m).sum() else None,
                                  "n": int(m.sum())}
    P(f"  {p}: corr(lsr pct, r10) pearson {c10:+.2f} spearman {s10:+.2f} | corr(lsr pct, r30) pearson {c30:+.2f} spearman {s30:+.2f} | spearman(raw lsr, r30) {craw30:+.2f}")
    P(f"     trailing 30d return: flagged(0.8) {b[flag8 & m].mean()*100:+.1f}%  flagged(0.9) {b[flag9 & m].mean()*100:+.1f}%  all {b[m].mean()*100:+.1f}% ; "
      f"share of flagged(0.8) days with negative trailing 30d: {(b[flag8 & m] < 0).mean():.2f}")

# conditional tests: flag AND trailing 30d return positive / negative. Use a derived column via cond mechanism.
df["_r30_btc"] = r30
df["_r30_pct_btc"] = r30_pct
OUT["confound"]["cond"] = {}
for t in (0.8, 0.9):
    OUT["confound"]["cond"][f"thr{t}_r30pos"] = run_cell(t, 1, cond=("_r30_btc", "raw", "top", 0.0), label=f"thr={t} AND trailing 30d return >= 0")
    OUT["confound"]["cond"][f"thr{t}_r30neg"] = run_cell(t, 1, cond=("_r30_btc", "raw", "bottom", -1e-12), label=f"thr={t} AND trailing 30d return < 0")

P("\n-- price-only control: trailing 30d return in its BOTTOM quintile / decile of the trailing 365 days (no lsr) --")
OUT["confound"]["price_only"] = {}
for t in (0.2, 0.1):
    spec = ("_r30_pct_btc", "raw", "bottom", t)
    r = H2.event_test2(df, spec, "btc", horizons=HORIZONS, lag=1, episode_bar=15)
    rr = ret_rows(r)
    risk = {}
    for W in WINDOWS:
        k = H2.risk_test(df, spec, "btc", windows=(W,), lag=1, crash=CRASH[W], episode_bar=20)
        risk.update(risk_rows(k))
    P(f"[price-only: r30 pct365 <= {t}, lag=1]")
    P(fmt_ret(rr)); P(fmt_risk(risk))
    OUT["confound"]["price_only"][str(t)] = {"ret": rr, "risk": risk}
# and the raw version: trailing 30d return < -10%
spec = ("_r30_btc", "raw", "bottom", -0.10)
r = H2.event_test2(df, spec, "btc", horizons=HORIZONS, lag=1, episode_bar=15)
rr = ret_rows(r); risk = {}
for W in WINDOWS:
    k = H2.risk_test(df, spec, "btc", windows=(W,), lag=1, crash=CRASH[W], episode_bar=20); risk.update(risk_rows(k))
P("[price-only: trailing 30d return < -10%, lag=1]"); P(fmt_ret(rr)); P(fmt_risk(risk))
OUT["confound"]["price_only"]["r30_lt_-10pct"] = {"ret": rr, "risk": risk}

# residual test: regress lsr pct on r30 (and r10) within each period's TRAILING data? Simpler: lsr pct residual vs r30 over the full
# sample is look-ahead; instead do a rolling 365d regression residual (past-only): resid_t = pct_t - a_t - b_t * r30_t with a,b from the trailing 365 days.
P("\n-- lsr pct ORTHOGONALISED to trailing 30d return (rolling 365d past-only OLS residual), then top quintile/decile of residual pct365 --")


def rolling_resid(y, x, w=365, mp=180):
    yv, xv = y.to_numpy(float), x.to_numpy(float)
    out = np.full(len(yv), np.nan)
    for i in range(len(yv)):
        lo = max(0, i - w + 1)
        ys, xs = yv[lo:i + 1], xv[lo:i + 1]
        m = ~(np.isnan(ys) | np.isnan(xs))
        if m.sum() < mp or np.isnan(yv[i]) or np.isnan(xv[i]):
            continue
        xm, ym = xs[m].mean(), ys[m].mean()
        vx = ((xs[m] - xm) ** 2).sum()
        b = ((xs[m] - xm) * (ys[m] - ym)).sum() / vx if vx > 0 else 0.0
        a = ym - b * xm
        out[i] = yv[i] - a - b * xv[i]
    return pd.Series(out, index=y.index)


resid = rolling_resid(sig_pct, r30)
df["_lsr_resid_btc"] = resid
OUT["confound"]["resid"] = {}
for t in (0.8, 0.9):
    spec = ("_lsr_resid_btc", "pct365", "top", t)
    r = H2.event_test2(df, spec, "btc", horizons=HORIZONS, lag=1, episode_bar=15)
    rr = ret_rows(r); risk = {}
    for W in WINDOWS:
        k = H2.risk_test(df, spec, "btc", windows=(W,), lag=1, crash=CRASH[W], episode_bar=20); risk.update(risk_rows(k))
    P(f"[lsr residual (net of trailing r30) pct365 >= {t}, lag=1]"); P(fmt_ret(rr)); P(fmt_risk(risk))
    OUT["confound"]["resid"][str(t)] = {"ret": rr, "risk": risk}

# ---------------------------------------------------------------------------------------------------------------
section("5. Excess against a TRAILING 365-day mean of the forward return (past-only drift), instead of the period mean")
OUT["trailing_excess"] = {}
for t in (0.8, 0.9):
    flag, _ = H2.make_flag(df, ("lsr_BTC", "pct365", "top", t), "1d", 1)
    OUT["trailing_excess"][str(t)] = {}
    P(f"[thr={t} lag=1] excess_trailing = fwd_h(t) - mean of fwd_h over the 365 days whose forward window ENDED by t (fully known at t)")
    for h in HORIZONS:
        fwd = px.shift(-h) / px - 1
        # the forward return starting at t-h-k is known at t when k>=0; trailing mean of known forward returns
        known = fwd.shift(h)  # fwd return of windows ending at t
        trail = known.rolling(365, min_periods=180).mean()
        ex = fwd - trail
        OUT["trailing_excess"][str(t)][h] = {}
        parts = []
        for p in H.PERIODS:
            f = H2.slice_period(flag, p, "1d"); y = H2.slice_period(ex, p, "1d")
            m = y.notna() & f.notna(); f, y = f[m], y[m]
            if f.sum() < 3:
                OUT["trailing_excess"][str(t)][h][p] = None; parts.append(f"{p[:3]} -"); continue
            mean_flag = float(y[f].mean()); mean_all = float(y.mean())
            t_nw, _ = H.nw_t(y.to_numpy(float), f.to_numpy(float), h)
            # t of the flagged mean itself vs zero (NW)
            t0 = H.nw_mean_t(y[f].to_numpy(float), h)
            n_ind = H2.clusters(y[f].index, h, "1d")
            OUT["trailing_excess"][str(t)][h][p] = {"mean_flag_excess_trailing": mean_flag, "mean_all_excess_trailing": mean_all,
                                                    "diff_flag_minus_all": mean_flag - mean_all, "t_nw_diff": t_nw, "t_nw_flag_vs_zero": t0, "n_ind": n_ind, "n_flag": int(f.sum())}
            parts.append(f"{p[:3]} flag {mean_flag*100:+.1f}% (t0={t0:.1f}) all {mean_all*100:+.1f}% diff {(mean_flag-mean_all)*100:+.1f}% t={t_nw:.1f} n={n_ind}")
        P(f"  h={h}: " + " | ".join(parts))

# ---------------------------------------------------------------------------------------------------------------
section("6. Drop the best 3 validation episodes (the 3 episodes with the most negative 90d excess), recompute validation")
OUT["drop3"] = {}
for t in (0.8, 0.9):
    flag, _ = H2.make_flag(df, ("lsr_BTC", "pct365", "top", t), "1d", 1)
    OUT["drop3"][str(t)] = {}
    for h in HORIZONS:
        fwd = px.shift(-h) / px - 1
        mdd = H2.forward_mdd(px, h)
        f = H2.slice_period(flag, "validation", "1d"); y = H2.slice_period(fwd, "validation", "1d"); d = H2.slice_period(mdd, "validation", "1d")
        m = y.notna(); f, y, d = f[m], y[m], d[m]
        eps = episodes(f, h)
        # assign each flagged day to its episode (cluster)
        starts = eps
        ep_id = pd.Series(np.nan, index=f.index)
        cur = -1
        last = None
        for dt in f[f].index:
            if last is None or (dt - last).days > h:
                cur += 1
            ep_id.loc[dt] = cur; last = dt
        ep_mean = {i: float(y[ep_id == i].mean() - y.mean()) for i in range(cur + 1)}
        ranked = sorted(ep_mean, key=lambda i: ep_mean[i])  # most negative first
        drop = set(ranked[:3])
        keep = f & ~ep_id.isin(drop)
        base_ex = float(y[f].mean() - y.mean()); base_t, _ = H.nw_t(y.to_numpy(float), f.to_numpy(float), h)
        if keep.sum() >= 3:
            ex2 = float(y[keep].mean() - y.mean()); t2, _ = H.nw_t(y.to_numpy(float), keep.to_numpy(float), h)
            dd2 = float(d[keep].mean() - d.mean())
        else:
            ex2 = t2 = dd2 = None
        dd_base = float(d[f].mean() - d.mean())
        OUT["drop3"][str(t)][h] = {"n_episodes": cur + 1, "dropped": [str(starts[i].date()) for i in sorted(drop)] if cur + 1 else [],
                                   "episode_excess": {str(starts[i].date()): ep_mean[i] for i in range(cur + 1)},
                                   "excess_before": base_ex, "t_before": base_t, "excess_after": ex2, "t_after": t2,
                                   "mdd_diff_before": dd_base, "mdd_diff_after": dd2, "n_flag_after": int(keep.sum())}
        P(f"  thr={t} h={h} validation: episodes {cur+1} -> per-episode excess {{{', '.join(f'{str(starts[i].date())}: {ep_mean[i]*100:+.1f}%' for i in range(cur+1))}}}")
        P(f"     before drop: ex {base_ex*100:+.1f}% t={base_t:.1f} mdd_diff {dd_base*100:+.1f} | after dropping {len(drop)}: ex {'-' if ex2 is None else f'{ex2*100:+.1f}%'} t={'-' if t2 is None else f'{t2:.1f}'} mdd_diff {'-' if dd2 is None else f'{dd2*100:+.1f}'} n_flag_after={int(keep.sum())}")

# ---------------------------------------------------------------------------------------------------------------
section("7. The lsr_BTC series: start, gaps, level shifts, top-decile dates, regime change")
s = df["lsr_BTC"]
OUT["series"] = {"first_valid": str(s.first_valid_index().date()), "last_valid": str(s.last_valid_index().date()), "n_valid": int(s.notna().sum())}
v = s.dropna(); gaps = v.index.to_series().diff().dt.days
OUT["series"]["gaps_gt1"] = {str(k.date()): int(g) for k, g in gaps[gaps > 1].items()}
P(f"  first valid {OUT['series']['first_valid']}  last valid {OUT['series']['last_valid']}  n valid {OUT['series']['n_valid']}  gaps>1d: {OUT['series']['gaps_gt1']}")
yr = s.groupby(s.index.year).agg(["count", "mean", "std", "min", "max", "median"])
P(yr.to_string())
OUT["series"]["yearly"] = {str(k): {c: (None if pd.isna(x) else float(x)) for c, x in row.items()} for k, row in yr.iterrows()}
q = s.groupby(s.index.to_period("Q")).agg(["mean", "std"])
P("  quarterly mean/std:"); P(q.round(3).to_string())
OUT["series"]["quarterly"] = {str(k): {c: (None if pd.isna(x) else float(x)) for c, x in row.items()} for k, row in q.iterrows()}
# day-to-day change distribution: jumps that look like a source change
dchg = s.diff().abs()
P("  largest 15 absolute day-to-day jumps in raw lsr:"); P(dchg.sort_values(ascending=False).head(15).round(3).to_string())
OUT["series"]["largest_jumps"] = {str(k.date()): float(x) for k, x in dchg.sort_values(ascending=False).head(15).items()}
# autocorrelation / persistence
P(f"  lag-1 autocorr raw lsr: {s.autocorr(1):.3f}  lag-5: {s.autocorr(5):.3f}  lag-30: {s.autocorr(30):.3f}")
# pct365 first valid date and top-decile dates by period
P(f"  pct365 first valid: {sig_pct.first_valid_index().date()}")
for t in (0.8, 0.9):
    fl = (sig_pct >= t) & sig_pct.notna()
    P(f"  flag(pct365>={t}) by year: " + str(fl.groupby(fl.index.year).sum().to_dict()))
    OUT["series"][f"flag_by_year_{t}"] = {str(k): int(x) for k, x in fl.groupby(fl.index.year).sum().items()}
top = (sig_pct >= 0.9) & sig_pct.notna()
eps9 = episodes(top, 15)
P(f"  top-decile episodes (clusters > 15 days apart), first day, raw lsr that day, trailing 30d ret, forward 30/60/90 ret:")
rows = []
for e in eps9:
    seg = top.loc[e:]
    # episode length
    length = 0
    for dt in seg.index:
        if seg.loc[dt]:
            length += 1
        else:
            break
    rows.append({"start": str(e.date()), "len": length, "lsr": float(s.loc[e]), "r30_trailing": float(r30.loc[e]) if not np.isnan(r30.loc[e]) else None,
                 "f30": float((px.shift(-30) / px - 1).loc[e]) if not np.isnan((px.shift(-30) / px - 1).loc[e]) else None,
                 "f60": float((px.shift(-60) / px - 1).loc[e]) if not np.isnan((px.shift(-60) / px - 1).loc[e]) else None,
                 "f90": float((px.shift(-90) / px - 1).loc[e]) if not np.isnan((px.shift(-90) / px - 1).loc[e]) else None})
for r in rows:
    P(f"    {r['start']} len={r['len']:3d} lsr={r['lsr']:.2f} r30_trail={'-' if r['r30_trailing'] is None else f'{r['r30_trailing']*100:+.1f}%'} "
      f"f30={'-' if r['f30'] is None else f'{r['f30']*100:+.1f}%'} f60={'-' if r['f60'] is None else f'{r['f60']*100:+.1f}%'} f90={'-' if r['f90'] is None else f'{r['f90']*100:+.1f}%'}")
OUT["series"]["top_decile_episodes"] = rows

# What is the pct365 flag really capturing in 2021? the 365d window in late 2020/2021 is the ramp from 1.3 to 2.1
P("\n  Level-shift check: pct365 top-quintile share by half-year (should be ~0.2 if stationary):")
hy = sig_pct.groupby([sig_pct.index.year, (sig_pct.index.month > 6).astype(int)]).apply(lambda x: float((x >= 0.8).mean()) if x.notna().any() else np.nan)
P(hy.round(2).to_string())
OUT["series"]["top_quintile_share_by_half"] = {f"{k[0]}H{k[1]+1}": (None if pd.isna(x) else float(x)) for k, x in hy.items()}

# Alternative detrended definition: pct365 of lsr relative to its 90d z-score (removes slow level drift)
P("\n  Alternative: z90 of lsr (removes slow level drift) >= 1.0 / 1.5, lag=1")
OUT["series"]["z90_alt"] = {}
for z in (1.0, 1.5):
    spec = ("lsr_BTC", "z90", "top", z)
    r = H2.event_test2(df, spec, "btc", horizons=HORIZONS, lag=1, episode_bar=15)
    rr = ret_rows(r); risk = {}
    for W in WINDOWS:
        k = H2.risk_test(df, spec, "btc", windows=(W,), lag=1, crash=CRASH[W], episode_bar=20); risk.update(risk_rows(k))
    P(f"[lsr z90 >= {z}, lag=1]"); P(fmt_ret(rr)); P(fmt_risk(risk))
    OUT["series"]["z90_alt"][str(z)] = {"ret": rr, "risk": risk}

# ---------------------------------------------------------------------------------------------------------------
section("8. ETH cross-check and ex-2021 train")
OUT["eth"] = {}
for t in (0.8, 0.9):
    spec = ("lsr_ETH", "pct365", "top", t)
    r = H2.event_test2(df, spec, "eth", horizons=HORIZONS, lag=1, episode_bar=15)
    rr = ret_rows(r)
    P(f"[ETH lsr_ETH pct365 >= {t}, lag=1]"); P(fmt_ret(rr))
    OUT["eth"][str(t)] = rr
# train split: 2020-11..2021-12 vs 2022-01..2024-06
P("\n  BTC train split by sub-period (lag=1), excess vs sub-period mean:")
OUT["train_split"] = {}
for t in (0.8, 0.9):
    flag, _ = H2.make_flag(df, ("lsr_BTC", "pct365", "top", t), "1d", 1)
    OUT["train_split"][str(t)] = {}
    for lo, hi in (("2020-01-01", "2021-12-31"), ("2022-01-01", "2024-06-30"), ("2022-01-01", "2022-12-31"), ("2023-01-01", "2024-06-30")):
        OUT["train_split"][str(t)][f"{lo}..{hi}"] = {}
        parts = []
        for h in HORIZONS:
            fwd = px.shift(-h) / px - 1
            mdd = H2.forward_mdd(px, h)
            f = flag[(flag.index >= lo) & (flag.index <= hi)]; y = fwd.reindex(f.index); d = mdd.reindex(f.index)
            m = y.notna(); f, y, d = f[m], y[m], d[m]
            if f.sum() < 3:
                parts.append(f"h={h} -"); OUT["train_split"][str(t)][f"{lo}..{hi}"][h] = None; continue
            ex = float(y[f].mean() - y.mean()); tt, _ = H.nw_t(y.to_numpy(float), f.to_numpy(float), h)
            dd = float(d[f].mean() - d.mean()); n = H2.clusters(y[f].index, h, "1d")
            OUT["train_split"][str(t)][f"{lo}..{hi}"][h] = {"excess": ex, "t_nw": tt, "mdd_diff": dd, "n_ind": n, "n_flag": int(f.sum())}
            parts.append(f"h={h} ex {ex*100:+.1f}% t={tt:.1f} mdd {dd*100:+.1f} n={n} ({int(f.sum())}d)")
        P(f"  thr={t} {lo}..{hi}: " + " | ".join(parts))


# ---------------------------------------------------------------------------------------------------------------
def clean(v):
    if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
        return None
    if isinstance(v, dict):
        return {str(k): clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    if isinstance(v, (np.floating, np.integer)):
        return clean(float(v))
    if isinstance(v, (pd.Timestamp,)):
        return str(v.date())
    return v


with open(os.path.join(HERE, "lsr_btc_refute.json"), "w") as fh:
    json.dump(clean(OUT), fh, indent=1)
P("\nwrote", os.path.join(HERE, "lsr_btc_refute.json"))
