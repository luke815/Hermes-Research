"""Refutation of the R2 finding: 'late in a long high-OI run is worse than early' (ETH futures_oi, 30-day mdd).

Writes results3/refute/R2_refute.json and results3/refute/R2_refute_stdout.txt. Reads only; modifies no existing file.

Steps (see the task): (1) reproduce via score3.duration_table; (2) list the calendar episodes in the >60 bucket;
(3) bucket-edge shifts and a sweep of the 'late' threshold; (4) price-duration and coin-denominated-OI controls plus a
stratified (price-duration-matched) excess; (5) one observation per run, sign tests; (6) BTC; (7) W=60.
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
import harness as H  # noqa: E402
import harness2 as H2  # noqa: E402
import harness3 as H3  # noqa: E402
import score3 as S3  # noqa: E402  (import only; nothing in score3 runs on import except makedirs of results3)

OUTDIR = HERE
LINES = []


def say(*p):
    s = " ".join(str(x) for x in p)
    print(s, flush=True)
    LINES.append(s)


def hyst_state(p, on=0.8, off=0.6):
    out = np.zeros(len(p), dtype=bool)
    st = False
    for i, v in enumerate(p.to_numpy()):
        if np.isnan(v):
            st = False
        elif v >= on:
            st = True
        elif v < off:
            st = False
        out[i] = st
    return pd.Series(out, index=p.index)


def runs_for(series, how):
    """Days-in-state for a raw series: how in {'consecutive','hysteresis'}; percentile pct365 (365, 180)."""
    p = H.pct_rank(series, 365, 180)
    if how == "consecutive":
        return H3.days_in_state(p >= 0.8)
    return H3.days_in_state(hyst_state(p))


def dur_table(run_raw, px, buckets, W=30, crash=-0.10):
    """Same statistics as score3.duration_table but takes the (unlagged) run series and price directly."""
    run = run_raw.shift(1)
    fwd = px.shift(-W) / px - 1
    mdd = H2.forward_mdd(px, W)
    table = {}
    for pname in H.PERIODS:
        r, y, m = (H2.slice_period(x, pname, "1d") for x in (run, fwd, mdd))
        ok = y.notna() & m.notna() & r.notna()
        r, y, m = r[ok], y[ok], m[ok]
        base_crash = float((m <= crash).mean()) if len(m) else None
        rows = {}
        for lo, hi in buckets:
            key = f"{lo}-{hi if hi < 100000 else 'inf'}"
            f = (r >= lo) & (r <= hi)
            n = int(f.sum())
            if n < 3:
                rows[key] = {"n": n}
                continue
            t_mdd, _ = H.nw_t(m.to_numpy(float), f.to_numpy(float), W)
            rows[key] = {"n": n, "n_ind": H2.clusters(y[f].index, W, "1d"),
                         "excess": float(y[f].mean() - y.mean()),
                         "mdd_diff": float(m[f].mean() - m.mean()), "t_mdd": t_mdd,
                         "crash_lift": float((m[f] <= crash).mean() / base_crash) if base_crash else None}
        table[pname] = rows
    return table


def fmt_table(table, keys):
    out = []
    for p in ("train", "validation", "test"):
        cells = []
        for k in keys:
            r = table.get(p, {}).get(k, {})
            if "mdd_diff" in r:
                cells.append(f"{k}: n={r['n']}/{r['n_ind']} mdd {r['mdd_diff'] * 100:+.1f} (t {r['t_mdd']:.1f}) lift {r['crash_lift']:.2f}")
            else:
                cells.append(f"{k}: n={r.get('n', 0)}")
        out.append(f"   {p[:3]}: " + " | ".join(cells))
    return "\n".join(out)


def keys_of(buckets):
    return [f"{lo}-{hi if hi < 100000 else 'inf'}" for lo, hi in buckets]


def spans(mask):
    """Contiguous True spans of a boolean Series -> list of (start, end, n)."""
    out = []
    idx = mask.index
    v = mask.to_numpy()
    i = 0
    while i < len(v):
        if v[i]:
            j = i
            while j + 1 < len(v) and v[j + 1]:
                j += 1
            out.append((idx[i], idx[j], j - i + 1))
            i = j + 1
        else:
            i += 1
    return out


def episodes_in_bucket(run_raw, px, lo, pname, W=30):
    """Calendar spans of days whose lagged run >= lo in a period, with the mean forward W-day mdd on those days,
    the run span itself (first day of the run to its end) and the peak run length."""
    run = run_raw.shift(1)
    mdd = H2.forward_mdd(px, W)
    r = H2.slice_period(run, pname, "1d")
    m = H2.slice_period(mdd, pname, "1d")
    ok = m.notna() & r.notna()
    flag = (r >= lo) & ok
    out = []
    for s, e, n in spans(flag):
        # the run that contains s started (s - run[s] + 1) days earlier (in calendar days; daily bars)
        start_run = s - pd.Timedelta(days=int(r.loc[s]) - 1)
        full_run = run_raw[(run_raw.index >= start_run)]
        # end of the run: first zero at or after s in the unlagged series
        zero_after = run_raw[(run_raw.index > s) & (run_raw == 0)]
        run_end = zero_after.index[0] - pd.Timedelta(days=1) if len(zero_after) else run_raw.index[-1]
        peak = int(run_raw[(run_raw.index >= start_run) & (run_raw.index <= run_end)].max())
        px_s = px.loc[s]
        px_e = px.loc[e]
        out.append({"bucket_days": f"{s.date()}..{e.date()}", "n_days": int(n),
                    "run_span": f"{start_run.date()}..{run_end.date()}", "peak_run": peak,
                    "mean_mdd30_in_bucket": float(m.loc[s:e].mean()),
                    "min_mdd30_in_bucket": float(m.loc[s:e].min()),
                    "px_first": float(px_s), "px_last": float(px_e)})
    return out


def binom_two_sided(k, n):
    if n == 0:
        return None
    p_lo = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    p_hi = sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n
    return float(min(1.0, 2 * min(p_lo, p_hi)))


def episode_level(run_raw, px, T=60, W=30, early_day=1):
    """One observation per run that reaches T days: mdd_W measured from the first day the LAGGED run is > T
    (i.e. entry the day after the run's day T+1... same convention as the bucket), paired with mdd_W from the run's
    early day (lagged run == early_day). Also the period mean mdd on that date's period."""
    run = run_raw.shift(1)
    mdd = H2.forward_mdd(px, W)
    rows = []
    v = run.to_numpy()
    idx = run.index
    i = 0
    while i < len(v):
        if not np.isnan(v[i]) and v[i] >= 1 and (i == 0 or np.isnan(v[i - 1]) or v[i - 1] == 0):
            # a run begins at i (lagged run == 1)
            j = i
            while j + 1 < len(v) and not np.isnan(v[j + 1]) and v[j + 1] >= 1:
                j += 1
            peak = int(np.nanmax(v[i:j + 1]))
            if peak > T:
                k = i + int(np.argmax(v[i:j + 1] > T))
                late_date, early_date = idx[k], idx[i + early_day - 1]
                pname = next((p for p in H.PERIODS if len(H2.slice_period(pd.Series([1], index=[late_date]), p, "1d"))), None)
                m_late = mdd.get(late_date, np.nan)
                m_early = mdd.get(early_date, np.nan)
                base = H2.slice_period(mdd, pname, "1d").mean() if pname else np.nan
                rows.append({"run_start": str(idx[i].date()), "run_end": str(idx[j].date()), "peak_run": peak,
                             "late_date": str(late_date.date()), "period": pname,
                             "mdd_late": None if np.isnan(m_late) else float(m_late),
                             "mdd_early": None if np.isnan(m_early) else float(m_early),
                             "period_mean_mdd": None if np.isnan(base) else float(base),
                             "late_minus_early": None if (np.isnan(m_late) or np.isnan(m_early)) else float(m_late - m_early),
                             "late_minus_base": None if (np.isnan(m_late) or np.isnan(base)) else float(m_late - base)})
            i = j + 1
        else:
            i += 1
    return rows


def sign_summary(rows, key):
    vals = [r[key] for r in rows if r.get(key) is not None]
    n = len(vals)
    neg = sum(1 for x in vals if x < 0)
    return {"n": n, "n_negative": neg, "p_two_sided": binom_two_sided(neg, n), "mean": float(np.mean(vals)) if n else None,
            "median": float(np.median(vals)) if n else None}


def main():
    d = S3.load_daily()
    out = {}
    B0 = ((1, 10), (11, 30), (31, 60), (61, 100000))
    K0 = keys_of(B0)

    # ------------------------------------------------------------ (1) reproduce
    say("==== (1) Reproduce score3.duration_table for ETH futures_oi (W=30) ====")
    rep = {}
    for a in ("eth", "btc"):
        for variant, col in (("consecutive", f"futures_oi_{a}_hi_run"), ("hysteresis", f"futures_oi_{a}_hyst_run")):
            res = S3.duration_table(d, f"futures_oi_{a}", a, col)
            rep[f"{a}:{variant}"] = res
            say(f"[repro] {a} futures_oi [{variant}] -> {res['verdict']}")
            say(fmt_table(res["table"], K0))
            # cross-check with the local implementation
            mine = dur_table(runs_for(d[f"futures_oi_{a}"], variant), H.price(d, a), B0)
            diffs = [abs(mine[p][k]["mdd_diff"] - res["table"][p][k]["mdd_diff"]) for p in ("train", "validation")
                     for k in K0 if "mdd_diff" in mine[p][k] and "mdd_diff" in res["table"][p][k]]
            say(f"   local re-implementation max |mdd_diff| discrepancy vs score3: {max(diffs):.2e}")
    out["reproduce"] = rep

    # ------------------------------------------------------------ (2) episodes
    say("\n==== (2) Calendar episodes making up the >60 bucket (lagged run >= 61), ETH and BTC ====")
    ep = {}
    for a in ("eth", "btc"):
        px = H.price(d, a)
        for variant in ("consecutive", "hysteresis"):
            rr = runs_for(d[f"futures_oi_{a}"], variant)
            for pname in ("train", "validation"):
                e = episodes_in_bucket(rr, px, 61, pname)
                ep[f"{a}:{variant}:{pname}"] = e
                say(f"[episodes] {a} {variant} {pname}: {len(e)} spans")
                for x in e:
                    say(f"   bucket days {x['bucket_days']} (n={x['n_days']}), run {x['run_span']} peak {x['peak_run']}d, "
                        f"mean mdd30 {x['mean_mdd30_in_bucket'] * 100:+.1f}% min {x['min_mdd30_in_bucket'] * 100:+.1f}%, px {x['px_first']:.0f}->{x['px_last']:.0f}")
    out["episodes"] = ep
    # the NaN gap on 2025-07-25 splits the summer-2025 run; show the run with OI forward-filled
    say("\n[episodes] NaN inside futures_oi on 2021-06-03/04, 2023-10-17, 2025-07-25 reset days_in_state. Forward-filled variant:")
    ff = {}
    for a in ("eth", "btc"):
        px = H.price(d, a)
        for variant in ("consecutive", "hysteresis"):
            rr = runs_for(d[f"futures_oi_{a}"].ffill(), variant)
            t = dur_table(rr, px, B0)
            ff[f"{a}:{variant}"] = t
            say(f"[ffill] {a} {variant}")
            say(fmt_table(t, K0))
            for pname in ("train", "validation"):
                e = episodes_in_bucket(rr, px, 61, pname)
                ff[f"{a}:{variant}:{pname}:episodes"] = e
                say(f"   {pname} spans: " + "; ".join(f"{x['bucket_days']} (n={x['n_days']}, peak {x['peak_run']}, mdd {x['mean_mdd30_in_bucket'] * 100:+.1f})" for x in e))
    out["ffill"] = ff

    # ------------------------------------------------------------ (3) bucket edges
    say("\n==== (3) Bucket edges shifted and the 'late' threshold swept (ETH futures_oi, W=30) ====")
    edges = {"base 10/30/60": B0,
             "-10: 1-5/6-20/21-50/>50": ((1, 5), (6, 20), (21, 50), (51, 100000)),
             "+10: 1-20/21-40/41-70/>70": ((1, 20), (21, 40), (41, 70), (71, 100000)),
             "20/40/60/80": ((1, 20), (21, 40), (41, 60), (61, 80), (81, 100000))}
    eg = {}
    for a in ("eth", "btc"):
        px = H.price(d, a)
        for variant in ("consecutive", "hysteresis"):
            rr = runs_for(d[f"futures_oi_{a}"], variant)
            for name, B in edges.items():
                t = dur_table(rr, px, B)
                eg[f"{a}:{variant}:{name}"] = t
                say(f"[edges] {a} {variant} {name}")
                say(fmt_table(t, keys_of(B)))
            # sweep: days with lagged run > T vs all days
            sweep = {}
            say(f"[sweep] {a} {variant}: late bucket = lagged run > T")
            for T in (30, 40, 50, 60, 70, 80, 90, 100, 120):
                t = dur_table(rr, px, ((T + 1, 100000),))
                k = keys_of(((T + 1, 100000),))[0]
                sweep[T] = t
                say("   T=%3d " % T + " | ".join(
                    f"{p[:3]} n={t[p][k].get('n', 0)}/{t[p][k].get('n_ind', 0)} mdd {t[p][k]['mdd_diff'] * 100:+.1f} (t {t[p][k]['t_mdd']:.1f})"
                    if "mdd_diff" in t[p][k] else f"{p[:3]} n={t[p][k].get('n', 0)}" for p in ("train", "validation")))
            eg[f"{a}:{variant}:sweep"] = sweep
    out["edges"] = eg

    # ------------------------------------------------------------ (4) controls
    say("\n==== (4) Controls: price-duration, coin-denominated OI, and OI>60 excess stratified by price-duration ====")
    ctl = {}
    for a in ("eth", "btc"):
        px = H.price(d, a)
        for variant in ("consecutive", "hysteresis"):
            # (4a) price pct365 >= 0.8 days-in-state
            rp = runs_for(px, variant)
            t = dur_table(rp, px, B0)
            ctl[f"{a}:{variant}:price_run"] = t
            say(f"[control price-run] {a} {variant}: days-in-state of PRICE pct365>=0.8")
            say(fmt_table(t, K0))
            for pname in ("train", "validation"):
                e = episodes_in_bucket(rp, px, 61, pname)
                ctl[f"{a}:{variant}:price_run:{pname}:episodes"] = e
                say(f"   {pname} >60 spans: " + "; ".join(f"{x['bucket_days']} (n={x['n_days']}, mdd {x['mean_mdd30_in_bucket'] * 100:+.1f})" for x in e))
            # (4b) coin-denominated OI
            coin_oi = d[f"futures_oi_{a}"] / px
            rc = runs_for(coin_oi, variant)
            t = dur_table(rc, px, B0)
            ctl[f"{a}:{variant}:coin_oi_run"] = t
            say(f"[control coin-OI run] {a} {variant}: days-in-state of (futures_oi/{a} price) pct365>=0.8")
            say(fmt_table(t, K0))
            for pname in ("train", "validation"):
                e = episodes_in_bucket(rc, px, 61, pname)
                ctl[f"{a}:{variant}:coin_oi_run:{pname}:episodes"] = e
                say(f"   {pname} >60 spans: " + "; ".join(f"{x['bucket_days']} (n={x['n_days']}, mdd {x['mean_mdd30_in_bucket'] * 100:+.1f})" for x in e))
            # (4c) overlap and stratified excess: OI-run>60 days vs all days in the same price-run bucket
            ro = runs_for(d[f"futures_oi_{a}"], variant).shift(1)
            rp1 = rp.shift(1)
            mdd = H2.forward_mdd(px, 30)
            strat = {}
            for pname in ("train", "validation"):
                o, p_, m = (H2.slice_period(x, pname, "1d") for x in (ro, rp1, mdd))
                ok = m.notna() & o.notna() & p_.notna()
                o, p_, m = o[ok], p_[ok], m[ok]
                late = o > 60
                if late.sum() < 3:
                    strat[pname] = {"n": int(late.sum())}
                    continue
                pb = pd.cut(p_, bins=[-1, 0, 10, 30, 60, 100000], labels=["0", "1-10", "11-30", "31-60", ">60"])
                comp = pd.crosstab(pb[late], columns="n")
                # stratified excess: for each late day, subtract the mean mdd of ALL days in its price bucket
                bucket_mean = m.groupby(pb, observed=False).mean()
                strat_ex = float((m[late] - pb[late].map(bucket_mean).astype(float)).mean())
                raw_ex = float(m[late].mean() - m.mean())
                # partial regression: mdd ~ late_OI + late_price (+ price-bucket dummies), NW t on late_OI
                X = pd.DataFrame({"oi_late": late.astype(float), "px_late": (p_ > 60).astype(float)})
                for lab in ["1-10", "11-30", "31-60"]:
                    X[f"px_{lab}"] = (pb == lab).astype(float)
                t_oi = nw_t_multi(m.to_numpy(float), X.to_numpy(float), 30)
                strat[pname] = {"n_late": int(late.sum()), "price_bucket_counts": {str(k): int(v) for k, v in comp["n"].items()},
                                "raw_excess_mdd": raw_ex, "stratified_excess_mdd": strat_ex,
                                "share_also_price_late": float((p_[late] > 60).mean()),
                                "mdd_price_late_all": float(m[p_ > 60].mean() - m.mean()) if (p_ > 60).sum() >= 3 else None,
                                "mdd_oi_late_not_price_late": float(m[late & ~(p_ > 60)].mean() - m.mean()) if (late & ~(p_ > 60)).sum() >= 3 else None,
                                "n_oi_late_not_price_late": int((late & ~(p_ > 60)).sum()),
                                "mdd_price_late_not_oi_late": float(m[(p_ > 60) & ~late].mean() - m.mean()) if ((p_ > 60) & ~late).sum() >= 3 else None,
                                "n_price_late_not_oi_late": int(((p_ > 60) & ~late).sum()),
                                "partial_t_oi_late_given_price": t_oi}
                say(f"[stratified] {a} {variant} {pname}: OI>60 days n={int(late.sum())}; price-run buckets of those days {dict(comp['n'])}; "
                    f"share also price>60 {strat[pname]['share_also_price_late']:.2f}; raw excess mdd {raw_ex * 100:+.1f} -> price-bucket-stratified {strat_ex * 100:+.1f}; "
                    f"partial NW t(OI>60 | price buckets) {t_oi:.1f}")
                say(f"      price>60 all days mdd {fmtp(strat[pname]['mdd_price_late_all'])} | OI>60 & not price>60 (n={strat[pname]['n_oi_late_not_price_late']}) mdd {fmtp(strat[pname]['mdd_oi_late_not_price_late'])} | "
                    f"price>60 & not OI>60 (n={strat[pname]['n_price_late_not_oi_late']}) mdd {fmtp(strat[pname]['mdd_price_late_not_oi_late'])}")
            ctl[f"{a}:{variant}:stratified"] = strat
    out["controls"] = ctl

    # ------------------------------------------------------------ (5) episode level
    say("\n==== (5) Episode level: one observation per run that passes 60 days (W=30) ====")
    el = {}
    for a in ("eth", "btc"):
        px = H.price(d, a)
        for variant in ("consecutive", "hysteresis"):
            for label, src in (("oi", d[f"futures_oi_{a}"]), ("oi_ffill", d[f"futures_oi_{a}"].ffill()), ("price", px), ("coin_oi", d[f"futures_oi_{a}"] / px)):
                rr = runs_for(src, variant)
                rows = episode_level(rr, px, T=60, W=30)
                tv = [r for r in rows if r["period"] in ("train", "validation")]
                s_pair = sign_summary(tv, "late_minus_early")
                s_base = sign_summary(tv, "late_minus_base")
                el[f"{a}:{variant}:{label}"] = {"rows": rows, "sign_late_minus_early": s_pair, "sign_late_minus_base": s_base}
                say(f"[episode] {a} {variant} {label}: runs>60d in train+val n={len(tv)}; late<early in {s_pair['n_negative']}/{s_pair['n']} (p={fmtq(s_pair['p_two_sided'])}, mean {fmtp(s_pair['mean'])}); "
                    f"late<period-mean in {s_base['n_negative']}/{s_base['n']} (p={fmtq(s_base['p_two_sided'])}, mean {fmtp(s_base['mean'])})")
                for r in rows:
                    say(f"      run {r['run_start']}..{r['run_end']} peak {r['peak_run']} [{r['period']}] late {r['late_date']}: mdd_late {fmtp(r['mdd_late'])} mdd_early {fmtp(r['mdd_early'])} base {fmtp(r['period_mean_mdd'])}")
    out["episode_level"] = el

    # ------------------------------------------------------------ (6) BTC agreement is in the tables above; summarize signs
    say("\n==== (6) BTC vs ETH agreement on '>60 worse than 1-10' (W=30), per period ====")
    agree = {}
    for variant in ("consecutive", "hysteresis"):
        for pname in ("train", "validation"):
            row = {}
            for a in ("eth", "btc"):
                t = rep[f"{a}:{variant}"]["table"][pname]
                lo, hi = t.get("1-10", {}).get("mdd_diff"), t.get("61-inf", {}).get("mdd_diff")
                row[a] = None if lo is None or hi is None else float(hi - lo)
            agree[f"{variant}:{pname}"] = row
            say(f"   {variant} {pname}: (>60 minus 1-10) mdd_diff eth {fmtp(row['eth'])} btc {fmtp(row['btc'])}")
    out["agreement"] = agree

    # ------------------------------------------------------------ (7) W=60
    say("\n==== (7) Forward 60-day drawdown version (crash -20%) ====")
    w60 = {}
    for a in ("eth", "btc"):
        px = H.price(d, a)
        for variant in ("consecutive", "hysteresis"):
            for label, src in (("oi", d[f"futures_oi_{a}"]), ("price", px), ("coin_oi", d[f"futures_oi_{a}"] / px)):
                rr = runs_for(src, variant)
                t = dur_table(rr, px, B0, W=60, crash=-0.20)
                w60[f"{a}:{variant}:{label}"] = t
                say(f"[W60] {a} {variant} {label}")
                say(fmt_table(t, K0))
                rows = episode_level(rr, px, T=60, W=60)
                tv = [r for r in rows if r["period"] in ("train", "validation")]
                sp, sb = sign_summary(tv, "late_minus_early"), sign_summary(tv, "late_minus_base")
                w60[f"{a}:{variant}:{label}:episode"] = {"rows": rows, "sign_late_minus_early": sp, "sign_late_minus_base": sb}
                say(f"   episode-level W60: late<early {sp['n_negative']}/{sp['n']} (p={fmtq(sp['p_two_sided'])}), late<base {sb['n_negative']}/{sb['n']} (p={fmtq(sb['p_two_sided'])})")
    out["W60"] = w60

    with open(os.path.join(OUTDIR, "R2_refute.json"), "w") as fh:
        json.dump(out, fh, indent=1, default=str)
    with open(os.path.join(OUTDIR, "R2_refute_stdout.txt"), "w") as fh:
        fh.write("\n".join(LINES))


def fmtp(x):
    return "-" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:+.1f}%"


def fmtq(x):
    return "-" if x is None else f"{x:.3f}"


def nw_t_multi(y, X, lag):
    """Newey-West t on the FIRST column of X (with intercept added), lag as in harness.nw_t."""
    m = ~(np.isnan(y) | np.isnan(X).any(axis=1))
    y, X = y[m], X[m]
    n = len(y)
    X = np.column_stack([np.ones(n), X])
    # drop constant/duplicate columns to keep XtX invertible
    keep = [0] + [j for j in range(1, X.shape[1]) if X[:, j].std() > 0]
    X = X[:, keep]
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ beta
    XtX_inv = np.linalg.pinv(X.T @ X)
    S = (X * e[:, None]).T @ (X * e[:, None])
    for l in range(1, lag + 1):
        w = 1 - l / (lag + 1)
        G = (X[l:] * e[l:, None]).T @ (X[:-l] * e[:-l, None])
        S += w * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    return float(beta[1] / np.sqrt(max(V[1, 1], 1e-18)))


if __name__ == "__main__":
    main()
