"""Refutation of the R1 finding: USD open interest at its 1-year top -> below-average 30-90d returns.

Written 2026-11-19 by the sceptical reviewer. Reads harness.py / harness2.py unchanged. Writes only under results3/refute/.

Sections
  S1  reproduce: USD OI top (perp_oi, futures_oi; 0.8, 0.9), price pct365 top 0.8 control, coin-OI (OI/price) pct365 top 0.8
  S2  decomposition: OLS of forward 60d return on [price_top, coinOI_top] (and [price_top, usdOI_top]) per period, NW lag 60;
      coin-OI top CONDITIONAL on price NOT top
  S3  episode-level: one observation per independent episode (gap > h bars), dates listed
  S4  excess against the trailing 365-day mean of h-day returns instead of the period mean
  S5  lag 2 and 5
  S6  dashboard OI (oi_BTC/oi_ETH, from 2022-09) as a second source; agreement with perp_oi flags
  S7  OI 30-day change top quintile (fast build-up), USD and coin terms
  S8  extra controls: excess vs the period mean over the SIGNAL-AVAILABLE sample only; ex-2021-22 train
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

OUT_JSON = os.path.join(HERE, "refute_oi.json")
df = pd.read_pickle(os.path.join(ROOT, "data", "daily2.pkl"))
HORIZONS = (30, 60, 90)
PER = ("train", "validation", "test")
RESULTS = {}
LOG = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.append(s)


# derived series: coin-denominated OI and the dashboard OI
for a in ("btc", "eth"):
    df[f"coin_perp_oi_{a}"] = df[f"perp_oi_{a}"] / df[a]
    df[f"coin_futures_oi_{a}"] = df[f"futures_oi_{a}"] / df[a]
    df[f"dash_oi_{a}"] = df[f"oi_{a.upper()}"]
    df[f"coin_dash_oi_{a}"] = df[f"oi_{a.upper()}"] / df[a]
    df[f"price_{a}"] = df[a]
    # 30-day percent change (harness2 has no pchg30 transform; H.pct_change is the harness definition)
    for base in (f"perp_oi_{a}", f"futures_oi_{a}", f"coin_perp_oi_{a}", f"coin_futures_oi_{a}", f"price_{a}"):
        df[f"pchg30_{base}"] = H.pct_change(df[base], 30)


def fwd_ret(px, h):
    return px.shift(-h) / px - 1


def slice_p(s, p):
    return H2.slice_period(s, p, "1d")


def episodes(index, h):
    """Split flagged dates into independent episodes: consecutive flagged dates more than h days apart start a new one."""
    if len(index) == 0:
        return []
    d = np.array(sorted(index))
    eps, cur = [], [d[0]]
    for prev, nxt in zip(d[:-1], d[1:]):
        if (nxt - prev) / np.timedelta64(1, "D") > h:
            eps.append(cur)
            cur = [nxt]
        else:
            cur.append(nxt)
    eps.append(cur)
    return eps


def cell(flag, px, h, period, baseline="period", avail=None):
    """Mean forward h-day return on flagged bars minus a baseline, NW t (lag h) of the flag coefficient, episode count.

    baseline: 'period' (harness definition: mean over all bars in the period with a forward return),
              'avail'  (mean over bars in the period where the signal is available: avail mask),
              'trail'  (per-bar trailing 365-day mean of realized h-day returns, known at t)."""
    fwd = fwd_ret(px, h)
    f, y = slice_p(flag, period), slice_p(fwd, period)
    m = y.notna()
    if baseline == "avail" and avail is not None:
        m = m & slice_p(avail, period).fillna(False)
    f, y = f[m].fillna(False).astype(bool), y[m]
    if f.sum() < 3 or (~f).sum() < 10:
        return {"n_flag": int(f.sum()), "n_ind": 0, "excess": None, "t_nw": None}
    if baseline == "trail":
        past = (px / px.shift(h) - 1).rolling(365, min_periods=180).mean()  # realized h-day returns ending at t
        base = slice_p(past, period)[m]
        yy = (y - base)
        mm = yy.notna()
        yy, ff, y = yy[mm], f[mm], y[mm]
        if ff.sum() < 3:
            return {"n_flag": int(ff.sum()), "n_ind": 0, "excess": None, "t_nw": None}
        ex = float(yy[ff].mean())
        t = H.nw_mean_t(yy[ff].to_numpy(float), h)  # NW t of the mean trailing-excess on flagged bars
        t2, _ = H.nw_t(yy.to_numpy(float), ff.to_numpy(float), h)
        return {"n_flag": int(ff.sum()), "n_ind": H2.clusters(yy[ff].index, h, "1d"), "excess": ex, "t_nw": float(t),
                "t_nw_vs_rest": float(t2), "mean_flag": float(y[ff].mean()), "hit": float((y[ff] > 0).mean())}
    ex = float(y[f].mean() - y.mean())
    t, _ = H.nw_t(y.to_numpy(float), f.to_numpy(float), h)
    return {"n_flag": int(f.sum()), "n_ind": H2.clusters(y[f].index, h, "1d"), "n_bars": int(m.sum()),
            "mean_flag": float(y[f].mean()), "mean_all": float(y.mean()), "excess": ex, "t_nw": float(t),
            "hit": float((y[f] > 0).mean())}


def fmt(r):
    if r.get("excess") is None:
        return f"- (n_flag={r.get('n_flag', 0)})"
    return f"ex {r['excess'] * 100:+6.1f}% t={r['t_nw']:+5.1f} n_ind={r['n_ind']:2d} n_flag={r['n_flag']:3d}"


def run_cell(name, flag, px, horizons=HORIZONS, baseline="period", avail=None, store=True):
    res = {}
    for h in horizons:
        res[h] = {p: cell(flag, px, h, p, baseline, avail) for p in PER}
        say(f"  {name:48s} h={h:2d}: " + " | ".join(f"{p[:3]} {fmt(res[h][p])}" for p in PER))
    if store:
        RESULTS.setdefault("cells", {})[name] = {str(h): v for h, v in res.items()}
    return res


def flag_of(series, transforms, side, thr, lag=1):
    f, s = H2.make_flag(df, (series, transforms, side, thr), "1d", lag)
    return f, s


# ------------------------------------------------------------------------------------------------------------
say("=" * 110)
say("S1. REPRODUCE: USD OI top, price-top control, coin-OI top (lag 1, excess vs period mean, NW t lag h)")
say("=" * 110)
flags = {}
for a in ("btc", "eth"):
    px = H.price(df, a)
    for src in ("perp_oi", "futures_oi"):
        for thr in (0.8, 0.9):
            f, s = flag_of(f"{src}_{a}", "pct365", "top", thr)
            flags[(a, f"usd_{src}", thr)] = (f, s)
            run_cell(f"{a} USD {src} pct365 top {thr}", f, px)
    f, s = flag_of(f"price_{a}", "pct365", "top", 0.8)
    flags[(a, "price", 0.8)] = (f, s)
    run_cell(f"{a} PRICE pct365 top 0.8 (control)", f, px)
    f, s = flag_of(f"price_{a}", "pct365", "top", 0.9)
    flags[(a, "price", 0.9)] = (f, s)
    run_cell(f"{a} PRICE pct365 top 0.9 (control)", f, px)
    for src in ("perp_oi", "futures_oi"):
        f, s = flag_of(f"coin_{src}_{a}", "pct365", "top", 0.8)
        flags[(a, f"coin_{src}", 0.8)] = (f, s)
        run_cell(f"{a} COIN {src}/price pct365 top 0.8", f, px)
        f, s = flag_of(f"coin_{src}_{a}", "pct365", "top", 0.9)
        flags[(a, f"coin_{src}", 0.9)] = (f, s)
        run_cell(f"{a} COIN {src}/price pct365 top 0.9", f, px)

# compare with the stored R1 json
say("\nComparison with results3/R1_overheating_long_horizon.json (excess, %):")
try:
    r1 = json.load(open(os.path.join(ROOT, "results3", "R1_overheating_long_horizon.json")))
    keys = [k for k in r1 if "perp_oi" in k or "futures_oi" in k]
    say("  keys found:", len(keys), keys[:6])
    for k in keys:
        v = r1[k]
        hz = v.get("horizons") or v.get("return", {}).get("horizons")
        if not hz:
            continue
        parts = []
        for h in ("30", "60", "90"):
            e = hz.get(h, {}).get("cell", {})
            parts.append(f"h{h} " + "/".join(f"{(e.get(p, {}).get('excess') or float('nan')) * 100:+.1f}" for p in PER))
        say(f"  R1 {k:40s} " + " | ".join(parts))
except Exception as exc:  # noqa: BLE001
    say("  could not parse R1 json:", exc)

# overlap statistics
say("\nOverlap of flags (bars flagged by both / bars flagged by OI), signal-available sample:")
RESULTS["overlap"] = {}
for a in ("btc", "eth"):
    for src in ("perp_oi", "futures_oi"):
        for thr in (0.8, 0.9):
            fo = flags[(a, f"usd_{src}", thr)][0]
            fp = flags[(a, "price", thr)][0]
            fc = flags[(a, f"coin_{src}", 0.8)][0]
            row = {}
            for p in PER:
                o, pp, c = slice_p(fo, p), slice_p(fp, p), slice_p(fc, p)
                row[p] = {"n_oi": int(o.sum()), "share_price_top": float((o & pp).sum() / o.sum()) if o.sum() else None,
                          "share_coin_top": float((o & c).sum() / o.sum()) if o.sum() else None,
                          "n_oi_not_price": int((o & ~pp).sum())}
            RESULTS["overlap"][f"{a}:{src}:{thr}"] = row
            say(f"  {a} {src} {thr}: " + " | ".join(
                f"{p[:3]} n={row[p]['n_oi']} price-top share={row[p]['share_price_top'] if row[p]['share_price_top'] is None else round(row[p]['share_price_top'], 2)} "
                f"coin-top share={row[p]['share_coin_top'] if row[p]['share_coin_top'] is None else round(row[p]['share_coin_top'], 2)} OI-not-price={row[p]['n_oi_not_price']}"
                for p in PER))

# log correlations by period
say("\ncorr(log OI, log price) by period (signal-available bars):")
for a in ("btc", "eth"):
    for src in ("perp_oi", "futures_oi"):
        parts = []
        for p in PER:
            sub = slice_p(df[[a, f"{src}_{a}"]], p).dropna()
            parts.append(f"{p[:3]} {np.corrcoef(np.log(sub[a]), np.log(sub[f'{src}_{a}']))[0, 1]:.2f} (n={len(sub)})")
        say(f"  {a} {src}: " + " | ".join(parts))

# ------------------------------------------------------------------------------------------------------------
say("\n" + "=" * 110)
say("S2. DECOMPOSITION: OLS fwd60 ~ const + price_top + coinOI_top (and + usdOI_top), NW lag 60, per period")
say("=" * 110)


def ols_nw(y, X, lag):
    """Multivariate OLS with Newey-West (Bartlett) standard errors. X includes the constant. Returns beta, t."""
    m = ~(np.isnan(y) | np.isnan(X).any(axis=1))
    y, X = y[m], X[m]
    n, k = X.shape
    if n < 30 or np.linalg.matrix_rank(X) < k:
        return np.full(k, np.nan), np.full(k, np.nan), n
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    e = y - X @ beta
    Xe = X * e[:, None]
    S = Xe.T @ Xe
    for l in range(1, lag + 1):
        w = 1 - l / (lag + 1)
        G = Xe[l:].T @ Xe[:-l]
        S += w * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    se = np.sqrt(np.maximum(np.diag(V), 1e-18))
    return beta, beta / se, n


RESULTS["ols"] = {}
for a in ("btc", "eth"):
    px = H.price(df, a)
    for src in ("perp_oi", "futures_oi"):
        avail = df[f"{src}_{a}"].notna() & flags[(a, "price", 0.8)][1].notna() & flags[(a, f"coin_{src}", 0.8)][1].notna()
        for h in (30, 60, 90):
            fwd = fwd_ret(px, h)
            for p in PER:
                m = slice_p(avail, p).fillna(False)
                y = slice_p(fwd, p)[m].to_numpy(float)
                P = slice_p(flags[(a, "price", 0.8)][0], p)[m].to_numpy(float)
                C = slice_p(flags[(a, f"coin_{src}", 0.8)][0], p)[m].to_numpy(float)
                U = slice_p(flags[(a, f"usd_{src}", 0.8)][0], p)[m].to_numpy(float)
                one = np.ones_like(y)
                b1, t1, n1 = ols_nw(y, np.column_stack([one, P, C]), h)
                b2, t2, n2 = ols_nw(y, np.column_stack([one, P, U]), h)
                b3, t3, n3 = ols_nw(y, np.column_stack([one, U]), h)
                b4, t4, n4 = ols_nw(y, np.column_stack([one, P]), h)
                b5, t5, n5 = ols_nw(y, np.column_stack([one, C]), h)
                key = f"{a}:{src}:h{h}:{p}"
                RESULTS["ols"][key] = {
                    "n": int(n1), "P_only": [float(b4[1]), float(t4[1])], "C_only": [float(b5[1]), float(t5[1])],
                    "U_only": [float(b3[1]), float(t3[1])],
                    "P|C": [float(b1[1]), float(t1[1])], "C|P": [float(b1[2]), float(t1[2])],
                    "P|U": [float(b2[1]), float(t2[1])], "U|P": [float(b2[2]), float(t2[2])],
                    "n_P": int(P.sum()), "n_C": int(C.sum()), "n_U": int(U.sum()), "n_C_notP": int(((C == 1) & (P == 0)).sum()),
                    "n_U_notP": int(((U == 1) & (P == 0)).sum())}
                say(f"  {a} {src} h={h} {p[:3]} n={n1:4d} | alone: P {b4[1] * 100:+6.1f} (t{t4[1]:+5.1f})  C {b5[1] * 100:+6.1f} (t{t5[1]:+5.1f})  U {b3[1] * 100:+6.1f} (t{t3[1]:+5.1f})"
                    f" | joint P+C: P {b1[1] * 100:+6.1f} (t{t1[1]:+5.1f}) C {b1[2] * 100:+6.1f} (t{t1[2]:+5.1f})"
                    f" | joint P+U: P {b2[1] * 100:+6.1f} (t{t2[1]:+5.1f}) U {b2[2] * 100:+6.1f} (t{t2[2]:+5.1f})"
                    f" | nP={int(P.sum())} nC={int(C.sum())} nU={int(U.sum())} C&!P={int(((C == 1) & (P == 0)).sum())} U&!P={int(((U == 1) & (P == 0)).sum())}")

say("\nS2b. coin-OI top CONDITIONAL on price NOT at top (pct365 < 0.8), and USD-OI top conditional on price NOT top; and price top conditional on OI NOT top")
for a in ("btc", "eth"):
    px = H.price(df, a)
    fp = flags[(a, "price", 0.8)][0]
    sp = flags[(a, "price", 0.8)][1]
    not_price_top = (sp < 0.8) & sp.notna()
    for src in ("perp_oi", "futures_oi"):
        fc = flags[(a, f"coin_{src}", 0.8)][0]
        fu = flags[(a, f"usd_{src}", 0.8)][0]
        sc = flags[(a, f"coin_{src}", 0.8)][1]
        run_cell(f"{a} COIN {src} top0.8 & price NOT top", fc & not_price_top, px)
        run_cell(f"{a} USD {src} top0.8 & price NOT top", fu & not_price_top, px)
        run_cell(f"{a} PRICE top0.8 & coin {src} NOT top", fp & (sc < 0.8) & sc.notna(), px)
        run_cell(f"{a} PRICE top0.8 & coin {src} top", fp & fc, px)

# ------------------------------------------------------------------------------------------------------------
say("\n" + "=" * 110)
say("S3. EPISODE-LEVEL: one observation per independent episode (gap > h bars); dates, bars, mean fwd return, excess vs period mean")
say("=" * 110)
RESULTS["episodes"] = {}


def episode_table(name, flag, px, h):
    fwd = fwd_ret(px, h)
    rows_all = []
    for p in PER:
        f, y = slice_p(flag, p), slice_p(fwd, p)
        m = y.notna()
        f, y = f[m].fillna(False).astype(bool), y[m]
        if f.sum() == 0:
            continue
        mean_all = float(y.mean())
        eps = episodes(y[f].index, h)
        ep_rows = []
        for e in eps:
            idx = pd.DatetimeIndex(e)
            r = y.loc[idx]
            ep_rows.append({"period": p, "start": str(idx[0].date()), "end": str(idx[-1].date()), "bars": int(len(idx)),
                            "mean_fwd": float(r.mean()), "first_fwd": float(r.iloc[0]), "excess": float(r.mean() - mean_all),
                            "share_neg": float((r < 0).mean())})
        exs = np.array([e["excess"] for e in ep_rows])
        wts = np.array([e["bars"] for e in ep_rows], float)
        summary = {"n_episodes": len(ep_rows), "mean_episode_excess": float(exs.mean()), "n_negative": int((exs < 0).sum()),
                   "bar_weighted_excess": float((exs * wts).sum() / wts.sum()),
                   "excess_dropping_worst": float(np.delete(exs, exs.argmin()).mean()) if len(exs) > 1 else None,
                   "worst_episode": ep_rows[int(exs.argmin())]["start"],
                   "share_bars_in_worst": float(wts[exs.argmin()] / wts.sum())}
        say(f"  {name} h={h} {p}: {len(ep_rows)} episodes, mean episode excess {exs.mean() * 100:+.1f}%, {int((exs < 0).sum())}/{len(exs)} negative, "
            f"bar-weighted {summary['bar_weighted_excess'] * 100:+.1f}%, dropping worst ({summary['worst_episode']}, {summary['share_bars_in_worst']:.0%} of bars) -> "
            f"{(summary['excess_dropping_worst'] or 0) * 100:+.1f}%")
        for e in ep_rows:
            say(f"      {e['start']}..{e['end']} bars={e['bars']:3d} mean fwd {e['mean_fwd'] * 100:+6.1f}% excess {e['excess'] * 100:+6.1f}% neg-share {e['share_neg']:.2f}")
        rows_all.append({"summary": summary, "episodes": ep_rows})
    RESULTS["episodes"][f"{name}:h{h}"] = rows_all


for a in ("btc", "eth"):
    px = H.price(df, a)
    for h in (30, 60):
        episode_table(f"{a} USD perp_oi top0.8", flags[(a, "usd_perp_oi", 0.8)][0], px, h)
        episode_table(f"{a} USD perp_oi top0.9", flags[(a, "usd_perp_oi", 0.9)][0], px, h)
        episode_table(f"{a} USD futures_oi top0.8", flags[(a, "usd_futures_oi", 0.8)][0], px, h)
        episode_table(f"{a} PRICE top0.8", flags[(a, "price", 0.8)][0], px, h)
        episode_table(f"{a} COIN perp_oi top0.8", flags[(a, "coin_perp_oi", 0.8)][0], px, h)

# ------------------------------------------------------------------------------------------------------------
say("\n" + "=" * 110)
say("S4. EXCESS vs TRAILING 365-day mean of realized h-day returns (known at t); t = NW t of the mean on flagged bars; also vs-rest t")
say("=" * 110)
for a in ("btc", "eth"):
    px = H.price(df, a)
    for thr in (0.8, 0.9):
        run_cell(f"{a} USD perp_oi top{thr} [trail365]", flags[(a, "usd_perp_oi", thr)][0], px, baseline="trail")
        run_cell(f"{a} USD futures_oi top{thr} [trail365]", flags[(a, "usd_futures_oi", thr)][0], px, baseline="trail")
    run_cell(f"{a} PRICE top0.8 [trail365]", flags[(a, "price", 0.8)][0], px, baseline="trail")
    run_cell(f"{a} COIN perp_oi top0.8 [trail365]", flags[(a, "coin_perp_oi", 0.8)][0], px, baseline="trail")
    run_cell(f"{a} COIN futures_oi top0.8 [trail365]", flags[(a, "coin_futures_oi", 0.8)][0], px, baseline="trail")

# ------------------------------------------------------------------------------------------------------------
say("\n" + "=" * 110)
say("S5. LAG 2 and LAG 5 (flag shifted 2 / 5 bars), excess vs period mean")
say("=" * 110)
for a in ("btc", "eth"):
    px = H.price(df, a)
    for lag in (2, 5):
        for src in ("perp_oi", "futures_oi"):
            for thr in (0.8, 0.9):
                f, _ = flag_of(f"{src}_{a}", "pct365", "top", thr, lag=lag)
                run_cell(f"{a} USD {src} top{thr} lag{lag}", f, px)
        f, _ = flag_of(f"price_{a}", "pct365", "top", 0.8, lag=lag)
        run_cell(f"{a} PRICE top0.8 lag{lag}", f, px)
        f, _ = flag_of(f"coin_perp_oi_{a}", "pct365", "top", 0.8, lag=lag)
        run_cell(f"{a} COIN perp_oi top0.8 lag{lag}", f, px)

# ------------------------------------------------------------------------------------------------------------
say("\n" + "=" * 110)
say("S6. DASHBOARD OI (oi_BTC / oi_ETH, from 2022-09-09; pct365 flags from ~2023-03) as a second source")
say("=" * 110)
RESULTS["dashboard_agreement"] = {}
for a in ("btc", "eth"):
    px = H.price(df, a)
    say(f"  log corr dashboard OI vs perp_oi (common sample): "
        f"{np.corrcoef(np.log(df[[f'dash_oi_{a}', f'perp_oi_{a}']].dropna()).T.values)[0, 1]:.3f}  -- near-identical series; agreement is largely by construction")
    for thr in (0.8, 0.9):
        fd, sd = flag_of(f"dash_oi_{a}", "pct365", "top", thr)
        run_cell(f"{a} DASH oi pct365 top {thr}", fd, px)
        # same thresholds on perp_oi restricted to the dashboard-available sample, for a like-for-like comparison
        fp_, sp_ = flags[(a, "usd_perp_oi", thr)]
        common = sd.notna()
        run_cell(f"{a} USD perp_oi top {thr} [dash sample only]", fp_ & common, px)
        agree = {}
        for p in PER:
            d_, p_ = slice_p(fd, p), slice_p(fp_ & common, p)
            both, either = int((d_ & p_).sum()), int((d_ | p_).sum())
            agree[p] = {"jaccard": both / either if either else None, "n_dash": int(d_.sum()), "n_perp": int(p_.sum())}
        RESULTS["dashboard_agreement"][f"{a}:{thr}"] = agree
        say(f"     flag agreement (Jaccard) dash vs perp_oi: " + " | ".join(
            f"{p[:3]} {agree[p]['jaccard'] if agree[p]['jaccard'] is None else round(agree[p]['jaccard'], 2)} (n {agree[p]['n_dash']}/{agree[p]['n_perp']})" for p in PER))
    fcd, _ = flag_of(f"coin_dash_oi_{a}", "pct365", "top", 0.8)
    run_cell(f"{a} COIN dash oi/price top 0.8", fcd, px)

# ------------------------------------------------------------------------------------------------------------
say("\n" + "=" * 110)
say("S7. ALTERNATIVE: OI 30-day CHANGE in its top quintile of the trailing year (fast build-up), USD and coin terms, lag 1")
say("=" * 110)
for a in ("btc", "eth"):
    px = H.price(df, a)
    for src in ("perp_oi", "futures_oi"):
        f, s = flag_of(f"pchg30_{src}_{a}", "pct365", "top", 0.8)
        run_cell(f"{a} USD {src} 30d-change pct365 top 0.8", f, px)
        f, s = flag_of(f"pchg30_coin_{src}_{a}", "pct365", "top", 0.8)
        run_cell(f"{a} COIN {src} 30d-change pct365 top 0.8", f, px)
        # raw threshold variant: USD OI up more than 30% in 30 days
        f, s = flag_of(f"pchg30_{src}_{a}", "raw", "top", 0.30)
        run_cell(f"{a} USD {src} 30d-change > +30% (raw)", f, px)
        f, s = flag_of(f"pchg30_coin_{src}_{a}", "raw", "top", 0.15)
        run_cell(f"{a} COIN {src} 30d-change > +15% (raw)", f, px)
    # price 30d change top quintile as the control for the fast build-up
    f, s = flag_of(f"pchg30_price_{a}", "pct365", "top", 0.8)
    run_cell(f"{a} PRICE 30d-change pct365 top 0.8 (control)", f, px)
    # fast build-up in coin terms AND price NOT up strongly
    fc, sc = flag_of(f"pchg30_coin_perp_oi_{a}", "pct365", "top", 0.8)
    fpp, spp = flag_of(f"pchg30_price_{a}", "pct365", "top", 0.8)
    run_cell(f"{a} COIN perp_oi 30d-chg top0.8 & price 30d-chg NOT top", fc & (spp < 0.8) & spp.notna(), px)
    # OI top AND fast build-up (late-stage crowding)
    run_cell(f"{a} USD perp_oi top0.8 & USD 30d-chg top0.8", flags[(a, "usd_perp_oi", 0.8)][0] & flag_of(f"pchg30_perp_oi_{a}", "pct365", "top", 0.8)[0], px)

# ------------------------------------------------------------------------------------------------------------
say("\n" + "=" * 110)
say("S8. EXTRA CONTROLS: (a) excess vs the period mean over the SIGNAL-AVAILABLE sample only (OI exists from 2021-03; pct365 flags from 2021-09);"
    " (b) train restricted to 2023-01-01..2024-06-30 (ex 2021-22)")
say("=" * 110)
for a in ("btc", "eth"):
    px = H.price(df, a)
    avail = flags[(a, "usd_perp_oi", 0.8)][1].notna()
    for thr in (0.8, 0.9):
        run_cell(f"{a} USD perp_oi top{thr} [avail-sample mean]", flags[(a, "usd_perp_oi", thr)][0], px, baseline="avail", avail=avail)
        run_cell(f"{a} USD futures_oi top{thr} [avail-sample mean]", flags[(a, "usd_futures_oi", thr)][0], px, baseline="avail", avail=avail)
    run_cell(f"{a} PRICE top0.8 [avail-sample mean]", flags[(a, "price", 0.8)][0], px, baseline="avail", avail=avail)
    run_cell(f"{a} COIN perp_oi top0.8 [avail-sample mean]", flags[(a, "coin_perp_oi", 0.8)][0], px, baseline="avail", avail=avail)

say("\n  (b) ex-2021-22: train sample 2023-01-01..2024-06-30 only (mean over that sample)")
RESULTS["ex2122"] = {}
for a in ("btc", "eth"):
    px = H.price(df, a)
    for name, key in (("USD perp_oi 0.8", ("usd_perp_oi", 0.8)), ("USD perp_oi 0.9", ("usd_perp_oi", 0.9)), ("USD futures_oi 0.8", ("usd_futures_oi", 0.8)),
                      ("PRICE 0.8", ("price", 0.8)), ("COIN perp_oi 0.8", ("coin_perp_oi", 0.8))):
        f = flags[(a, *key)][0]
        parts = []
        for h in HORIZONS:
            fwd = fwd_ret(px, h)
            m = (fwd.index >= "2023-01-01") & (fwd.index <= "2024-06-30") & fwd.notna()
            y, ff = fwd[m], f[m].fillna(False).astype(bool)
            if ff.sum() < 3:
                parts.append(f"h{h} -")
                RESULTS["ex2122"][f"{a}:{name}:h{h}"] = None
                continue
            ex = float(y[ff].mean() - y.mean())
            t, _ = H.nw_t(y.to_numpy(float), ff.to_numpy(float), h)
            n_ind = H2.clusters(y[ff].index, h, "1d")
            RESULTS["ex2122"][f"{a}:{name}:h{h}"] = {"excess": ex, "t_nw": float(t), "n_ind": n_ind, "n_flag": int(ff.sum())}
            parts.append(f"h{h} ex {ex * 100:+.1f}% t={t:+.1f} n_ind={n_ind} n_flag={int(ff.sum())}")
        say(f"  {a} {name:20s} train-ex2122: " + " | ".join(parts))

# yearly breakdown of flagged bars: where do the USD-OI-top bars sit?
say("\n  Flagged bars by calendar year (USD perp_oi top 0.8 / price top 0.8 / coin perp_oi top 0.8):")
RESULTS["years"] = {}
for a in ("btc", "eth"):
    yrs = {}
    for lab, key in (("usd", ("usd_perp_oi", 0.8)), ("price", ("price", 0.8)), ("coin", ("coin_perp_oi", 0.8))):
        f = flags[(a, *key)][0]
        yrs[lab] = f.groupby(f.index.year).sum().astype(int).to_dict()
    RESULTS["years"][a] = yrs
    years = sorted(set().union(*[set(v) for v in yrs.values()]))
    say(f"  {a}: " + " ".join(f"{y}[usd {yrs['usd'].get(y, 0)} price {yrs['price'].get(y, 0)} coin {yrs['coin'].get(y, 0)}]" for y in years if y >= 2021))

# ------------------------------------------------------------------------------------------------------------
# save


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


with open(OUT_JSON, "w") as fh:
    json.dump(clean(RESULTS), fh, indent=1)
with open(os.path.join(HERE, "refute_oi_stdout.txt"), "w") as fh:
    fh.write("\n".join(LOG))
say(f"\nwritten {OUT_JSON}")
