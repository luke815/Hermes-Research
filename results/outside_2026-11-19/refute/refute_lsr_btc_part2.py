"""Part 2: episode day-weights, circular-shift placebo p-values, residual-variant episode dates, ETH episode-level.
Writes results3/refute/lsr_btc_refute_part2.json. Read-only on everything else."""
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
HORIZONS = (30, 60, 90)
OUT = {}


def P(*a):
    print(*a, flush=True)


def clusters_of(flag, h):
    """List of (start, end, n_days) for clusters of flagged days separated by more than h days."""
    idx = flag[flag].index
    out = []
    if len(idx) == 0:
        return out
    start = idx[0]; prev = idx[0]; n = 1
    for dt in idx[1:]:
        if (dt - prev).days > h:
            out.append((start, prev, n)); start = dt; n = 0
        n += 1; prev = dt
    out.append((start, prev, n))
    return out


# ------------------------------------------------------------------------------------------------------------
P("=" * 100); P("A. Episode day-weights: each cluster's n flagged days, mean excess over ITS days, contribution to the period excess"); P("=" * 100)
OUT["weights"] = {}
for thr in (0.8, 0.9):
    flag, _ = H2.make_flag(df, ("lsr_BTC", "pct365", "top", thr), "1d", 1)
    OUT["weights"][str(thr)] = {}
    for h in HORIZONS:
        fwd = px.shift(-h) / px - 1
        mdd = H2.forward_mdd(px, h)
        OUT["weights"][str(thr)][h] = {}
        for p in H.PERIODS:
            f = H2.slice_period(flag, p, "1d"); y = H2.slice_period(fwd, p, "1d"); d = H2.slice_period(mdd, p, "1d")
            m = y.notna(); f, y, d = f[m], y[m], d[m]
            if f.sum() == 0:
                continue
            tot_ex = float(y[f].mean() - y.mean())
            cl = clusters_of(f, h)
            rows = []
            for (a, b, n) in cl:
                seg = f.loc[a:b]; days = seg[seg].index
                ex = float(y.loc[days].mean() - y.mean()); dd = float(d.loc[days].mean() - d.mean())
                contrib = ex * n / f.sum()
                rows.append({"start": str(a.date()), "end": str(b.date()), "n_days": int(n), "share": float(n / f.sum()), "mean_excess": ex, "contrib_to_excess": contrib, "mean_mdd_diff": dd})
            OUT["weights"][str(thr)][h][p] = {"period_excess": tot_ex, "n_flag": int(f.sum()), "clusters": rows}
            P(f"thr={thr} h={h} {p}: period excess {tot_ex*100:+.1f}% from {int(f.sum())} flagged days in {len(cl)} clusters")
            for r in rows:
                P(f"    {r['start']}..{r['end']} n={r['n_days']:3d} ({r['share']:.0%}) mean_ex {r['mean_excess']*100:+.1f}% contrib {r['contrib_to_excess']*100:+.1f}pp mdd_diff {r['mean_mdd_diff']*100:+.1f}")

# ------------------------------------------------------------------------------------------------------------
P("\n" + "=" * 100); P("B. Circular-shift placebo: shift the flag within each period by a random offset (keeps run lengths), 4000 shifts; two-sided p"); P("=" * 100)
rng = np.random.default_rng(20261119)
NSHIFT = 4000
OUT["placebo"] = {}


def placebo(flag_p, y, h, nshift=NSHIFT):
    fv = flag_p.to_numpy(bool); yv = y.to_numpy(float)
    n = len(fv)
    obs = yv[fv].mean() - yv.mean()
    # shifts at least h away from 0 so the placebo does not overlap the real flag much
    offs = rng.integers(h, n - h, size=nshift)
    stats = np.empty(nshift)
    for i, o in enumerate(offs):
        fs = np.roll(fv, o)
        stats[i] = yv[fs].mean() - yv.mean()
    p_two = float((np.abs(stats) >= abs(obs)).mean())
    p_one = float((stats <= obs).mean()) if obs < 0 else float((stats >= obs).mean())
    return obs, p_two, p_one, float(np.std(stats))


for thr in (0.8, 0.9):
    flag, _ = H2.make_flag(df, ("lsr_BTC", "pct365", "top", thr), "1d", 1)
    OUT["placebo"][str(thr)] = {}
    for h in HORIZONS:
        fwd = px.shift(-h) / px - 1
        mdd = H2.forward_mdd(px, h)
        OUT["placebo"][str(thr)][h] = {}
        parts_r = []; parts_d = []
        for p in H.PERIODS:
            f = H2.slice_period(flag, p, "1d"); y = H2.slice_period(fwd, p, "1d"); d = H2.slice_period(mdd, p, "1d")
            m = y.notna() & d.notna(); f, y, d = f[m], y[m], d[m]
            if f.sum() < 3:
                continue
            o, p2, p1, sd = placebo(f, y, h)
            od, pd2, pd1, sdd = placebo(f, d, h)
            OUT["placebo"][str(thr)][h][p] = {"excess": o, "p_two": p2, "p_one": p1, "placebo_sd": sd, "mdd_diff": od, "mdd_p_two": pd2, "mdd_p_one": pd1, "mdd_placebo_sd": sdd}
            parts_r.append(f"{p[:3]} ex {o*100:+.1f}% p2={p2:.2f} p1={p1:.2f} (sd {sd*100:.1f})")
            parts_d.append(f"{p[:3]} mdd {od*100:+.1f} p2={pd2:.2f} p1={pd1:.2f} (sd {sdd*100:.1f})")
        P(f"thr={thr} h={h} RET: " + " | ".join(parts_r))
        P(f"thr={thr} W={h} MDD: " + " | ".join(parts_d))

# joint: product of one-sided p across periods is not a valid combined test with 3 draws of tiny n; report the count of periods with p1<0.1
# ------------------------------------------------------------------------------------------------------------
P("\n" + "=" * 100); P("C. Residual variant (lsr pct net of trailing 30d return): which episodes, what overlap with the raw flag, placebo p"); P("=" * 100)
sig_pct = H2.transform(df["lsr_BTC"], "pct365")
r30 = px / px.shift(30) - 1


def rolling_resid(y, x, w=365, mp=180):
    yv, xv = y.to_numpy(float), x.to_numpy(float)
    out = np.full(len(yv), np.nan)
    for i in range(len(yv)):
        lo = max(0, i - w + 1)
        ys, xs = yv[lo:i + 1], xv[lo:i + 1]
        mm = ~(np.isnan(ys) | np.isnan(xs))
        if mm.sum() < mp or np.isnan(yv[i]) or np.isnan(xv[i]):
            continue
        xm, ym = xs[mm].mean(), ys[mm].mean()
        vx = ((xs[mm] - xm) ** 2).sum()
        b = ((xs[mm] - xm) * (ys[mm] - ym)).sum() / vx if vx > 0 else 0.0
        out[i] = yv[i] - (ym - b * xm) - b * xv[i]
    return pd.Series(out, index=y.index)


df["_lsr_resid_btc"] = rolling_resid(sig_pct, r30)
OUT["resid"] = {}
for thr in (0.8, 0.9):
    flag_res, _ = H2.make_flag(df, ("_lsr_resid_btc", "pct365", "top", thr), "1d", 1)
    flag_raw, _ = H2.make_flag(df, ("lsr_BTC", "pct365", "top", thr), "1d", 1)
    OUT["resid"][str(thr)] = {}
    P(f"[resid thr={thr}] flagged days by year: {flag_res.groupby(flag_res.index.year).sum().to_dict()}")
    for p in H.PERIODS:
        fr = H2.slice_period(flag_res, p, "1d"); fw = H2.slice_period(flag_raw, p, "1d")
        both = (fr & fw).sum(); P(f"   {p}: resid flags {int(fr.sum())}, raw flags {int(fw.sum())}, overlap {int(both)} ({both/max(1,fr.sum()):.0%} of resid)")
    for h in HORIZONS:
        fwd = px.shift(-h) / px - 1; mdd = H2.forward_mdd(px, h)
        OUT["resid"][str(thr)][h] = {}
        for p in H.PERIODS:
            f = H2.slice_period(flag_res, p, "1d"); y = H2.slice_period(fwd, p, "1d"); d = H2.slice_period(mdd, p, "1d")
            m = y.notna() & d.notna(); f, y, d = f[m], y[m], d[m]
            if f.sum() < 3:
                OUT["resid"][str(thr)][h][p] = None; continue
            cl = clusters_of(f, h)
            o, p2, p1, sd = placebo(f, y, h)
            od, pd2, pd1, sdd = placebo(f, d, h)
            # first-day episode excess
            eps = [(str(a.date()), int(n), float(y.loc[a] - y.mean())) for (a, b, n) in cl]
            OUT["resid"][str(thr)][h][p] = {"excess": o, "p_two": p2, "p_one": p1, "mdd_diff": od, "mdd_p_two": pd2, "n_flag": int(f.sum()), "clusters": eps}
            P(f"   h={h} {p}: ex {o*100:+.1f}% placebo p2={p2:.2f} p1={p1:.2f} | mdd {od*100:+.1f} p2={pd2:.2f} | n_flag {int(f.sum())} clusters {[(a, n, round(e*100,1)) for a, n, e in eps]}")

# ------------------------------------------------------------------------------------------------------------
P("\n" + "=" * 100); P("D. ETH lsr_ETH episode-level (first day of cluster), lag=1, thr 0.8 / 0.9"); P("=" * 100)
pxe = H.price(df, "eth")
OUT["eth_episodes"] = {}
for thr in (0.8, 0.9):
    flag, _ = H2.make_flag(df, ("lsr_ETH", "pct365", "top", thr), "1d", 1)
    OUT["eth_episodes"][str(thr)] = {}
    for h in HORIZONS:
        fwd = pxe.shift(-h) / pxe - 1
        OUT["eth_episodes"][str(thr)][h] = {}
        parts = []
        for p in H.PERIODS:
            f = H2.slice_period(flag, p, "1d"); y = H2.slice_period(fwd, p, "1d")
            m = y.notna(); f, y = f[m], y[m]
            cl = clusters_of(f, h)
            ex = [float(y.loc[a] - y.mean()) for (a, b, n) in cl]
            neg = sum(1 for v in ex if v < 0)
            OUT["eth_episodes"][str(thr)][h][p] = {"n_ep": len(ex), "n_neg": neg, "mean": float(np.mean(ex)) if ex else None, "dates": [str(a.date()) for (a, b, n) in cl], "excess": ex}
            parts.append(f"{p[:3]} n={len(ex)} neg={neg} mean={'-' if not ex else f'{np.mean(ex)*100:+.1f}%'}")
        P(f"ETH thr={thr} h={h}: " + " | ".join(parts))

# ------------------------------------------------------------------------------------------------------------
P("\n" + "=" * 100); P("E. Test period in detail: 2026 flagged clusters at thr 0.8 and the BTC path"); P("=" * 100)
flag, sig = H2.make_flag(df, ("lsr_BTC", "pct365", "top", 0.8), "1d", 1)
f26 = flag[flag.index >= "2025-12-01"]
for (a, b, n) in clusters_of(f26, 15):
    P(f"   cluster {a.date()}..{b.date()} n={n}: BTC at start {px.loc[a]:.0f}, +30d {px.shift(-30).loc[a]:.0f}, +60d {px.shift(-60).loc[a] if not np.isnan(px.shift(-60).loc[a]) else float('nan'):.0f}, +90d {px.shift(-90).loc[a] if not np.isnan(px.shift(-90).loc[a]) else float('nan'):.0f}")
P(f"   BTC month-end closes 2025-10..2026-11: " + ", ".join(f"{k.strftime('%Y-%m')}: {v:.0f}" for k, v in px[px.index >= '2025-10-01'].resample('ME').last().items()))
P(f"   test-period mean fwd 30/60/90: " + ", ".join(f"{h}: {H2.slice_period(px.shift(-h)/px-1, 'test', '1d').mean()*100:+.1f}%" for h in HORIZONS))


def clean(v):
    if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
        return None
    if isinstance(v, dict):
        return {str(k): clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    if isinstance(v, (np.floating, np.integer)):
        return clean(float(v))
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


with open(os.path.join(HERE, "lsr_btc_refute_part2.json"), "w") as fh:
    json.dump(clean(OUT), fh, indent=1)
P("\nwrote", os.path.join(HERE, "lsr_btc_refute_part2.json"))
