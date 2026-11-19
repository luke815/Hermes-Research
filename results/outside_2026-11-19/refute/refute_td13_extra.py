"""Extra controls for the TD buy-13 refutation (see refute_td13.py):
  A day-by-day mean return path after completion     D ex-2020 train
  B mechanical countdown-density control              E countdown count buckets: is 13 special?
  C short-term momentum controls (3d / 5d return)     F cross-asset pooled episodes, shared dates counted once
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, HERE)
import harness as H  # noqa: E402
import harness2 as H2  # noqa: E402
import harness3 as H3  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))
LINES = []
RES = {}


def say(*p):
    s = " ".join(str(x) for x in p)
    print(s, flush=True)
    LINES.append(s)


def fmt(r, horizons=(3, 5)):
    parts = []
    for h in horizons:
        e = r["horizons"][h]["cell"]
        bits = []
        for p in ("train", "validation", "test"):
            c = e.get(p, {})
            if c.get("excess") is None:
                bits.append(f"{p[:3]} - (n_flag={c.get('n_flag', 0)})")
            else:
                bits.append(f"{p[:3]} {c['excess'] * 100:+.2f}% t={c['t_nw']:.1f} ep={c['n_ind']}")
        parts.append(f"h={h}: " + " | ".join(bits))
    return "\n   ".join(parts)


def cells(r, horizons):
    return {h: {p: {k: r["horizons"][h]["cell"][p].get(k) for k in ("excess", "t_nw", "n_ind", "n_flag")}
                for p in ("train", "validation", "test")} for h in horizons}


d = pd.read_pickle(os.path.join(HERE, "data", "daily2.pkl"))
for a in ("btc", "eth"):
    H3.td_columns(d, a)
HZ = (1, 3, 5, 10, 20)

# ------------------------------------------------------------------ A. day-by-day path
say("==== A. MEAN DAILY RETURN PATH AFTER COMPLETION (day k = close[t+k]/close[t+k-1]-1, minus the period's mean daily return) ====")
RES["path"] = {}
for a in ("btc", "eth"):
    px = H.price(d, a)
    r1 = px / px.shift(1) - 1
    flag = d[f"td_buy13_{a}"] == 1
    RES["path"][a] = {}
    for per in ("train", "validation"):
        lo, hi = H.PERIODS[per]
        idx = d.index[flag]
        idx = idx[(idx >= pd.Timestamp(lo)) if lo else slice(None)] if lo else idx
        idx = idx[idx <= pd.Timestamp(hi)] if hi else idx
        base = H2.slice_period(r1, per, "1d").mean()
        path = []
        for k in range(1, 11):
            vals = []
            for t in idx:
                i = d.index.get_loc(t)
                if i + k < len(d):
                    vals.append(r1.iloc[i + k])
            vals = np.array(vals)
            path.append({"k": k, "mean_ex": float(vals.mean() - base), "share_neg": float((vals < 0).mean()), "n": int(len(vals))})
        say(f"[{a}] {per} (n={len(idx)}): " + " ".join(f"d{p['k']}:{p['mean_ex'] * 100:+.1f}%({int(p['share_neg'] * 100)}%neg)" for p in path))
        RES["path"][a][per] = path
say("   (lag-1 entry holds days 2..1+h; lag-0 holds days 1..h; the day-1 bar is the entry day's own move)")

# ------------------------------------------------------------------ B. mechanical density control
say("\n==== B. MECHANICAL CONTROL: count of bars with close <= close[2 earlier] in the trailing window (no DeMark structure) ====")
RES["density"] = {}
for a in ("btc", "eth"):
    px = H.price(d, a)
    q = (px <= px.shift(2)).astype(float)
    RES["density"][a] = {}
    for W in (20, 30):
        d[f"cdd{W}_{a}"] = q.rolling(W).sum()
        for nm, spec in ((f"density{W} top decile", (f"cdd{W}_{a}", "pct365", "top", 0.9)),
                         (f"density{W} >= 13", (f"cdd{W}_{a}", "raw", "top", 13))):
            r = H2.event_test2(d, spec, a, horizons=HZ, lag=1)
            n = int(H2.make_flag(d, spec, "1d", 1)[0].sum())
            say(f"[{a}] {nm} (n_flag={n}):\n   " + fmt(r, HZ))
            RES["density"][a][nm] = {"n_flag": n, "cells": cells(r, HZ)}
    # how dense were the actual completions?
    f = d[f"td_buy13_{a}"] == 1
    say(f"[{a}] at buy13 completion: trailing-20 density median {d[f'cdd20_{a}'][f].median():.0f}, min {d[f'cdd20_{a}'][f].min():.0f}, max {d[f'cdd20_{a}'][f].max():.0f}; "
        f"pct365 of density median {H.pct_rank(d[f'cdd20_{a}'], 365, 180)[f].median():.2f}")

# ------------------------------------------------------------------ C. short-term momentum controls
say("\n==== C. SHORT-TERM MOMENTUM CONTROLS (trailing 3d / 5d return bottom quintile and decile, pct365) ====")
RES["short_mom"] = {}
for a in ("btc", "eth"):
    px = H.price(d, a)
    d[f"ret3_{a}"] = px / px.shift(3) - 1
    d[f"ret5_{a}"] = px / px.shift(5) - 1
    RES["short_mom"][a] = {}
    for k in (3, 5):
        for thr in (0.2, 0.1):
            spec = (f"ret{k}_{a}", "pct365", "bottom", thr)
            r = H2.event_test2(d, spec, a, horizons=HZ, lag=1)
            say(f"[{a}] ret{k} bottom {'quintile' if thr == 0.2 else 'decile'}:\n   " + fmt(r, (3, 5, 10)))
            RES["short_mom"][a][f"ret{k}_{thr}"] = cells(r, (3, 5, 10))
    f = d[f"td_buy13_{a}"] == 1
    p3 = H.pct_rank(d[f"ret3_{a}"], 365, 180); p5 = H.pct_rank(d[f"ret5_{a}"], 365, 180)
    say(f"[{a}] at completion: ret3 pct median {p3[f].median():.2f} (bottom quintile share {(p3[f] <= 0.2).mean():.2f}); ret5 pct median {p5[f].median():.2f} (bottom quintile share {(p5[f] <= 0.2).mean():.2f})")
    RES["short_mom"][a]["at_completion"] = {"ret3pct_median": float(p3[f].median()), "ret3_bottomq_share": float((p3[f] <= 0.2).mean()),
                                            "ret5pct_median": float(p5[f].median()), "ret5_bottomq_share": float((p5[f] <= 0.2).mean())}

# ------------------------------------------------------------------ D. ex-2020 train
say("\n==== D. EX-2020 TRAIN (pre-registered refutation) ====")
RES["ex2020"] = {}
for a in ("btc", "eth"):
    px = H.price(d, a)
    flag = (d[f"td_buy13_{a}"] == 1).shift(1).fillna(False).astype(bool)
    RES["ex2020"][a] = {}
    for h in (3, 5):
        fwd = px.shift(-h) / px - 1
        f, y = H2.slice_period(flag, "train", "1d"), H2.slice_period(fwd, "train", "1d")
        keep = y.index.year != 2020
        f, y = f[keep], y[keep]
        m = y.notna(); f, y = f[m], y[m]
        ex = float(y[f].mean() - y.mean()); t, _ = H.nw_t(y.to_numpy(float), f.to_numpy(float), h)
        say(f"[{a}] train ex-2020 h={h}: excess {ex * 100:+.2f}% t={t:+.1f} n={int(f.sum())}")
        RES["ex2020"][a][f"h{h}"] = {"excess": ex, "t": float(t), "n": int(f.sum())}

# ------------------------------------------------------------------ E. countdown count buckets
say("\n==== E. IS 13 SPECIAL? Forward excess on every qualifying bar of an active buy countdown, by the count reached on that bar ====")


def countdown_counts(close):
    """Returns the buy-countdown count on each qualifying bar (1..13), 0 elsewhere; same rules as harness3 on closes."""
    c = close.to_numpy(float); n = len(c)
    out = np.zeros(n); b_count = s_count = 0; cd_buy = None; cd_sell = None
    for i in range(n):
        if i < 4 or np.isnan(c[i]) or np.isnan(c[i - 4]):
            b_count = s_count = 0; continue
        if c[i] < c[i - 4]:
            b_count += 1; s_count = 0
        elif c[i] > c[i - 4]:
            s_count += 1; b_count = 0
        else:
            b_count = s_count = 0
        if b_count == 9:
            cd_buy = 0; cd_sell = None
        if s_count == 9:
            cd_sell = 0; cd_buy = None
        if cd_buy is not None and i >= 2 and c[i] <= c[i - 2]:
            cd_buy += 1; out[i] = cd_buy
            if cd_buy == 13:
                cd_buy = None
        if cd_sell is not None and i >= 2 and c[i] >= c[i - 2]:
            cd_sell += 1
            if cd_sell == 13:
                cd_sell = None
    return pd.Series(out, index=close.index)


RES["buckets"] = {}
for a in ("btc", "eth"):
    px = H.price(d, a)
    cnt = countdown_counts(px)
    d[f"cdcount_{a}"] = cnt
    assert int((cnt == 13).sum()) == int(d[f"td_buy13_{a}"].sum())
    RES["buckets"][a] = {}
    for h in (3, 5):
        fwd = px.shift(-h) / px - 1
        line = []
        for per in ("train", "validation"):
            c_, y = H2.slice_period(cnt.shift(1), per, "1d"), H2.slice_period(fwd, per, "1d")
            m = y.notna() & c_.notna(); c_, y = c_[m], y[m]
            base = y.mean()
            for nm, sel in (("1-4", (c_ >= 1) & (c_ <= 4)), ("5-8", (c_ >= 5) & (c_ <= 8)), ("9-12", (c_ >= 9) & (c_ <= 12)), ("13", c_ == 13),
                            ("any 1-12", (c_ >= 1) & (c_ <= 12))):
                if sel.sum() >= 3:
                    ex = float(y[sel].mean() - base); t, _ = H.nw_t(y.to_numpy(float), sel.to_numpy(float), h)
                    line.append(f"{per[:3]} cnt {nm}: {ex * 100:+.2f}% (t {t:+.1f}, n={int(sel.sum())})")
                    RES["buckets"][a][f"{per}_h{h}_{nm}"] = {"excess": ex, "t": float(t), "n": int(sel.sum())}
        say(f"[{a}] h={h}: " + " | ".join(line))

# ------------------------------------------------------------------ F. cross-asset pooled episodes
say("\n==== F. CROSS-ASSET POOL: BTC and ETH completions as one event set; an ETH completion within 5 days of a BTC one is the same market episode and is dropped ====")
RES["pooled"] = {}
rng = np.random.default_rng(7)
NDRAW = 5000
bt = d.index[d["td_buy13_btc"] == 1]; et = d.index[d["td_buy13_eth"] == 1]
eth_keep = [t for t in et if not (abs((bt - t).days) <= 5).any()]
say(f"BTC completions {len(bt)}, ETH {len(et)}, ETH kept as independent {len(eth_keep)} -> pooled market episodes {len(bt) + len(eth_keep)}")
pb, pe = H.price(d, "btc"), H.price(d, "eth")
for h in (3, 5):
    fb, fe = pb.shift(-h) / pb - 1, pe.shift(-h) / pe - 1
    for per in ("train", "validation"):
        yb, ye = H2.slice_period(fb, per, "1d").dropna(), H2.slice_period(fe, per, "1d").dropna()
        ev = []
        for t in bt:
            i = d.index.get_loc(t)
            if i + 1 < len(d) and d.index[i + 1] in yb.index:
                ev.append(("btc", t, yb.loc[d.index[i + 1]] - yb.mean()))
        for t in eth_keep:
            i = d.index.get_loc(t)
            if i + 1 < len(d) and d.index[i + 1] in ye.index:
                ev.append(("eth", t, ye.loc[d.index[i + 1]] - ye.mean()))
        ex = np.array([e[2] for e in ev]); n = len(ex)
        nb = sum(1 for e in ev if e[0] == "btc"); ne = n - nb
        # placebo: nb random BTC bars + ne random ETH bars, independent draws
        ybv, yev = yb.to_numpy(float), ye.to_numpy(float)
        rand = np.array([(ybv[rng.choice(len(ybv), nb, replace=False)].sum() - nb * ybv.mean() + (yev[rng.choice(len(yev), ne, replace=False)].sum() - ne * yev.mean() if ne else 0)) / n for _ in range(NDRAW)])
        p = float((rand <= ex.mean()).mean())
        loo = [np.delete(ex, k).mean() for k in range(n)]
        worst = ev[int(np.argmin(ex))]
        say(f"h={h} {per}: pooled episodes {n} (btc {nb}, eth {ne}); mean excess {ex.mean() * 100:+.2f}%, negative {int((ex < 0).sum())}/{n}, median {np.median(ex) * 100:+.2f}%; "
            f"placebo p(<=obs)={p:.3f}; leave-one-out range [{min(loo) * 100:+.2f}%, {max(loo) * 100:+.2f}%]; worst {worst[0]} {worst[1].strftime('%Y-%m-%d')} ({worst[2] * 100:+.1f}%)")
        RES["pooled"][f"{per}_h{h}"] = {"n": n, "n_btc": nb, "n_eth": ne, "mean_excess": float(ex.mean()), "share_negative": float((ex < 0).mean()),
                                        "median": float(np.median(ex)), "p_placebo": p, "loo_min": float(min(loo)), "loo_max": float(max(loo)),
                                        "episodes": [{"asset": e[0], "signal": e[1].strftime("%Y-%m-%d"), "excess": float(e[2])} for e in ev]}
    # train+validation together: sign test on independent episodes
    allex = []
    for per in ("train", "validation"):
        allex += [e["excess"] for e in RES["pooled"][f"{per}_h{h}"]["episodes"]]
    allex = np.array(allex); k = int((allex < 0).sum()); n = len(allex)
    # two-sided binomial p without scipy
    from math import comb
    p_bin = sum(comb(n, j) for j in range(k, n + 1)) / 2 ** n
    say(f"h={h} train+validation: {k}/{n} independent market episodes negative; one-sided binomial p={p_bin:.3f}; mean {allex.mean() * 100:+.2f}%, median {np.median(allex) * 100:+.2f}%")
    RES["pooled"][f"all_h{h}"] = {"n": n, "k_negative": k, "p_binomial_one_sided": p_bin, "mean": float(allex.mean()), "median": float(np.median(allex))}

with open(os.path.join(OUT, "refute_td13_extra.json"), "w") as fh:
    json.dump(RES, fh, indent=1, default=str)
with open(os.path.join(OUT, "refute_td13_extra_stdout.txt"), "w") as fh:
    fh.write("\n".join(LINES))
say(f"\nwritten: refute_td13_extra.json, refute_td13_extra_stdout.txt in {OUT}")
