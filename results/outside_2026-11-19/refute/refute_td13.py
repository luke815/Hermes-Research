"""Refutation of: "TD buy countdown 13 on daily bars -> further weakness over 3-5 days (BTC and ETH, train and validation)".

Source cell: results3/R4_td_sequential.json ["1d"][":btc:buy13" | ":eth:buy13"]. Nothing outside results3/refute is written.

Tests
 1 reproduce (lag 1)                     5 countdown variants: close-vs-close (identity check), 12, 14, strict <, no cancel
 2 lag 2                                 6 3-day bars, three anchors (from the JSON and recomputed with dates)
 3 episode table with dates              7 placebo: random dates matched on count; random dates matched on count AND
 4 downtrend confound                      drawn only from bottom-quintile trailing-20d-return bars
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


def period_of(ts):
    for name, (lo, hi) in H.PERIODS.items():
        if (lo is None or ts >= pd.Timestamp(lo)) and (hi is None or ts <= pd.Timestamp(hi)):
            return name
    return "?"


def cell_summary(r, horizons=(1, 3, 5, 10, 20)):
    """excess, t, n_ind, n_flag per period per horizon as a compact dict."""
    out = {}
    for h in horizons:
        e = r["horizons"][h]["cell"]
        out[h] = {p: {k: e[p].get(k) for k in ("excess", "t_nw", "n_ind", "n_flag")} for p in ("train", "validation", "test")}
    return out


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


# ------------------------------------------------------------------ data
d = pd.read_pickle(os.path.join(HERE, "data", "daily2.pkl"))
for a in ("btc", "eth"):
    H3.td_columns(d, a)
    px = H.price(d, a)
    d[f"ret20_{a}"] = px / px.shift(20) - 1
    d[f"ret60_{a}"] = px / px.shift(60) - 1
    d[f"ret20pct_{a}"] = H.pct_rank(d[f"ret20_{a}"], 365, 180)
    d[f"ret60pct_{a}"] = H.pct_rank(d[f"ret60_{a}"], 365, 180)
    d[f"dd60_{a}"] = px / px.rolling(60).max() - 1

with open(os.path.join(HERE, "results3", "R4_td_sequential.json")) as fh:
    R4 = json.load(fh)

HZ = (1, 3, 5, 10, 20)

# ------------------------------------------------------------------ 1. reproduce
say("==== 1. REPRODUCE (daily, lag 1, excess = mean fwd return on flagged bars - period mean) ====")
RES["reproduce"] = {}
for a in ("btc", "eth"):
    spec = (f"td_buy13_{a}", "raw", "top", 1)
    r = H2.event_test2(d, spec, a, horizons=HZ, lag=1)
    j = R4["1d"][f":{a}:buy13"]["ret"]["horizons"]
    match = all(abs((r["horizons"][h]["cell"][p]["excess"] or 0) - (j[str(h)]["cell"][p]["excess"] or 0)) < 1e-9
                for h in HZ for p in ("train", "validation") if j[str(h)]["cell"][p].get("excess") is not None)
    say(f"[{a}] completions total {int(d[f'td_buy13_{a}'].sum())}; matches stored JSON: {match}")
    say("   " + fmt(r, HZ))
    RES["reproduce"][a] = {"matches_json": bool(match), "cells": cell_summary(r)}

# ------------------------------------------------------------------ 2. lag 2
say("\n==== 2. LAG 2 (enter two bars after the completion bar) ====")
RES["lag2"] = {}
for a in ("btc", "eth"):
    spec = (f"td_buy13_{a}", "raw", "top", 1)
    r = H2.event_test2(d, spec, a, horizons=HZ, lag=2)
    say(f"[{a}] lag 2:\n   " + fmt(r, HZ))
    RES["lag2"][a] = cell_summary(r)
# also lag 0 for reference (position at the completion close itself)
RES["lag0"] = {}
for a in ("btc", "eth"):
    r = H2.event_test2(d, (f"td_buy13_{a}", "raw", "top", 1), a, horizons=HZ, lag=0)
    say(f"[{a}] lag 0 (reference only):\n   " + fmt(r, (3, 5)))
    RES["lag0"][a] = cell_summary(r, (3, 5))

# ------------------------------------------------------------------ 3. episode table
say("\n==== 3. EPISODE TABLE (signal date = completion bar; entry = next close; fwd returns from the entry close) ====")
RES["episodes"] = {}
ep_tables = {}
for a in ("btc", "eth"):
    px = H.price(d, a)
    flag = d[f"td_buy13_{a}"] == 1
    rows = []
    for t in d.index[flag]:
        i = d.index.get_loc(t)
        if i + 1 >= len(d):
            continue
        e = d.index[i + 1]
        row = {"signal": t.strftime("%Y-%m-%d"), "entry": e.strftime("%Y-%m-%d"), "period": period_of(e)}
        for h in (1, 3, 5, 10, 20):
            if i + 1 + h < len(d):
                fwd_h = (px.shift(-h) / px - 1)
                per = period_of(e)
                yper = H2.slice_period(fwd_h, per, "1d").dropna()
                row[f"fwd{h}"] = float(fwd_h.iloc[i + 1])
                row[f"ex{h}"] = float(fwd_h.iloc[i + 1] - yper.mean())
            else:
                row[f"fwd{h}"] = None; row[f"ex{h}"] = None
        row["ret20"] = float(d[f"ret20_{a}"].iloc[i]); row["ret20pct"] = float(d[f"ret20pct_{a}"].iloc[i])
        row["ret60"] = float(d[f"ret60_{a}"].iloc[i]); row["ret60pct"] = float(d[f"ret60pct_{a}"].iloc[i])
        row["dd60"] = float(d[f"dd60_{a}"].iloc[i])
        rows.append(row)
    tab = pd.DataFrame(rows)
    ep_tables[a] = tab
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    show = tab[["signal", "period", "fwd3", "ex3", "fwd5", "ex5", "fwd10", "ret20", "ret20pct", "ret60pct", "dd60"]].copy()
    for c in ("fwd3", "ex3", "fwd5", "ex5", "fwd10", "ret20", "dd60"):
        show[c] = (show[c] * 100).round(1)
    for c in ("ret20pct", "ret60pct"):
        show[c] = show[c].round(2)
    say(f"[{a}] {len(tab)} completions with an entry bar")
    say(show.to_string(index=False))
    # per period: mean excess, share negative, leave-one-out range
    for per in ("train", "validation"):
        sub = tab[tab.period == per]
        for h in (3, 5):
            ex = sub[f"ex{h}"].dropna().to_numpy()
            if len(ex) == 0:
                continue
            loo = [np.delete(ex, k).mean() for k in range(len(ex))]
            say(f"   {per} h={h}: n={len(ex)} mean excess {ex.mean() * 100:+.2f}%  negative {int((ex < 0).sum())}/{len(ex)}  "
                f"median {np.median(ex) * 100:+.2f}%  leave-one-out range [{min(loo) * 100:+.2f}%, {max(loo) * 100:+.2f}%]  "
                f"worst single episode {sub.loc[sub[f'ex{h}'].idxmin(), 'signal']} ({ex.min() * 100:+.1f}%)")
    RES["episodes"][a] = json.loads(tab.to_json(orient="records"))
# overlap of BTC and ETH completion dates (are the two assets independent evidence?)
bd = set(ep_tables["btc"].signal); ed = set(ep_tables["eth"].signal)
b_idx = pd.to_datetime(sorted(bd)); e_idx = pd.to_datetime(sorted(ed))
near = sum(1 for t in e_idx if (abs((b_idx - t).days) <= 5).any())
say(f"\nBTC/ETH completion dates: exact same date {len(bd & ed)}; ETH completions within 5 days of a BTC completion: {near}/{len(ed)}")
RES["episodes"]["btc_eth_same_date"] = len(bd & ed)
RES["episodes"]["eth_within_5d_of_btc"] = near
val_b = ep_tables["btc"][ep_tables["btc"].period == "validation"]; val_e = ep_tables["eth"][ep_tables["eth"].period == "validation"]
say("validation BTC episodes: " + ", ".join(val_b.signal))
say("validation ETH episodes: " + ", ".join(val_e.signal))
RES["episodes"]["validation_dates"] = {"btc": list(val_b.signal), "eth": list(val_e.signal)}

# ------------------------------------------------------------------ 4. downtrend confound
say("\n==== 4. DOWNTREND CONFOUND ====")
RES["confound"] = {}
for a in ("btc", "eth"):
    say(f"[{a}] state at completion: trailing-20d-return percentile (pct365) distribution: "
        + ", ".join(f"{q}={ep_tables[a].ret20pct.quantile(q):.2f}" for q in (0.1, 0.5, 0.9))
        + f"; share in bottom quintile {(ep_tables[a].ret20pct <= 0.2).mean():.2f}, bottom decile {(ep_tables[a].ret20pct <= 0.1).mean():.2f}; "
        + f"60d-return bottom quintile {(ep_tables[a].ret60pct <= 0.2).mean():.2f}")
    RES["confound"][a] = {"share_ret20_bottom_q": float((ep_tables[a].ret20pct <= 0.2).mean()),
                          "share_ret20_bottom_d": float((ep_tables[a].ret20pct <= 0.1).mean()),
                          "share_ret60_bottom_q": float((ep_tables[a].ret60pct <= 0.2).mean())}
    # 4a: generic downtrend flags at the same horizons
    for col, thr, nm in ((f"ret20_{a}", 0.2, "ret20 bottom quintile"), (f"ret20_{a}", 0.1, "ret20 bottom decile"),
                         (f"ret60_{a}", 0.2, "ret60 bottom quintile"), (f"ret60_{a}", 0.1, "ret60 bottom decile")):
        r = H2.event_test2(d, (col, "pct365", "bottom", thr), a, horizons=HZ, lag=1)
        say(f"[{a}] control {nm} (lag 1):\n   " + fmt(r, HZ))
        RES["confound"][a][nm] = cell_summary(r)
    # 4b: buy13 conditional on trailing 20d return NOT in the bottom quintile (and the complement)
    d[f"td_buy13_notdown_{a}"] = ((d[f"td_buy13_{a}"] == 1) & (d[f"ret20pct_{a}"] > 0.2)).astype(float)
    d[f"td_buy13_down_{a}"] = ((d[f"td_buy13_{a}"] == 1) & (d[f"ret20pct_{a}"] <= 0.2)).astype(float)
    for nm in ("notdown", "down"):
        n = int(d[f"td_buy13_{nm}_{a}"].sum())
        r = H2.event_test2(d, (f"td_buy13_{nm}_{a}", "raw", "top", 1), a, horizons=HZ, lag=1)
        say(f"[{a}] buy13 AND ret20 {'NOT ' if nm == 'notdown' else ''}in bottom quintile: {n} completions\n   " + fmt(r, HZ))
        RES["confound"][a][f"buy13_{nm}"] = {"n": n, "cells": cell_summary(r)}
    # 4c: excess of buy13 measured against DOWNTREND bars only (same period, ret20 pct <= 0.2), with NW t inside that subsample
    px = H.price(d, a)
    flag = (d[f"td_buy13_{a}"] == 1).shift(1).fillna(False).astype(bool)
    downq = (d[f"ret20pct_{a}"] <= 0.2).shift(1).fillna(False).astype(bool)
    RES["confound"][a]["excess_vs_downtrend_bars"] = {}
    for h in (3, 5, 10):
        fwd = px.shift(-h) / px - 1
        for per in ("train", "validation"):
            f, y, q = (H2.slice_period(x, per, "1d") for x in (flag, fwd, downq))
            m = y.notna()
            f, y, q = f[m], y[m], q[m]
            if f.sum() < 3:
                continue
            ex_all = float(y[f].mean() - y.mean())
            ex_dq = float(y[f].mean() - y[q].mean())
            # within-downtrend test: bars in the bottom quintile only, flag = buy13 (which is almost always inside q)
            yy, ff = y[q | f].to_numpy(float), f[q | f].to_numpy(float)
            t_in, n_in = H.nw_t(yy, ff, h)
            say(f"[{a}] h={h} {per}: buy13 mean fwd {y[f].mean() * 100:+.2f}% | all bars {y.mean() * 100:+.2f}% | bottom-quintile-ret20 bars {y[q].mean() * 100:+.2f}% "
                f"(n={int(q.sum())}) -> excess vs all {ex_all * 100:+.2f}%, excess vs downtrend bars {ex_dq * 100:+.2f}% (NW t within downtrend bars {t_in:+.1f})")
            RES["confound"][a]["excess_vs_downtrend_bars"][f"{per}_h{h}"] = {"mean_flag": float(y[f].mean()), "mean_all": float(y.mean()),
                                                                              "mean_downq": float(y[q].mean()), "excess_all": ex_all,
                                                                              "excess_vs_downq": ex_dq, "t_within_downq": float(t_in) if t_in == t_in else None}

# ------------------------------------------------------------------ 5. countdown variants
say("\n==== 5. COUNTDOWN VARIANTS ====")


def td_variant(close, n_count=13, strict=False, cancel=True):
    """Same as harness3.td_sequential on closes (the daily panel has no highs/lows, so low == close there),
    with the countdown length, a strict inequality and the cancel-by-opposite-setup rule as parameters."""
    c = close.to_numpy(float)
    n = len(c)
    buy = np.zeros(n); sell = np.zeros(n)
    b_count = s_count = 0
    cd_buy = None; cd_sell = None
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
        if b_count == 9:
            cd_buy = 0
            if cancel:
                cd_sell = None
        if s_count == 9:
            cd_sell = 0
            if cancel:
                cd_buy = None
        if cd_buy is not None and i >= 2 and not np.isnan(c[i - 2]):
            hit = c[i] < c[i - 2] if strict else c[i] <= c[i - 2]
            if hit:
                cd_buy += 1
                if cd_buy == n_count:
                    buy[i] = 1; cd_buy = None
        if cd_sell is not None and i >= 2 and not np.isnan(c[i - 2]):
            hit = c[i] > c[i - 2] if strict else c[i] >= c[i - 2]
            if hit:
                cd_sell += 1
                if cd_sell == n_count:
                    sell[i] = 1; cd_sell = None
    return pd.Series(buy, index=close.index), pd.Series(sell, index=close.index)


RES["variants"] = {}
for a in ("btc", "eth"):
    px = H.price(d, a)
    b13, _ = td_variant(px, 13)
    ident = bool((b13.to_numpy() == d[f"td_buy13_{a}"].to_numpy()).all())
    say(f"[{a}] countdown 'close <= close[2 earlier]' identical to the harness3 flag (which used low=close): {ident}")
    RES["variants"][a] = {"close_vs_close_identical_to_original": ident}
    for nm, kw in (("count12", dict(n_count=12)), ("count14", dict(n_count=14)), ("count13_strict", dict(strict=True)),
                   ("count13_nocancel", dict(cancel=False)), ("count11", dict(n_count=11)), ("count15", dict(n_count=15))):
        b, _ = td_variant(px, **kw)
        col = f"td_buyvar_{nm}_{a}"
        d[col] = b
        n = int(b.sum())
        dates = [t.strftime("%Y-%m-%d") for t in d.index[b == 1]]
        r = H2.event_test2(d, (col, "raw", "top", 1), a, horizons=HZ, lag=1)
        say(f"[{a}] {nm}: {n} completions\n   " + fmt(r, HZ))
        RES["variants"][a][nm] = {"n": n, "dates": dates, "cells": cell_summary(r)}

# ------------------------------------------------------------------ 6. three-day bars
say("\n==== 6. THREE-DAY BARS (every third daily close, anchors 0/1/2) ====")
RES["three_day"] = {}
for k in (0, 1, 2):
    d3 = d.iloc[k::3].copy()
    for a in ("btc", "eth"):
        H3.td_columns(d3, a)
        col = f"td_buy13_{a}"
        n = int(d3[col].sum())
        dates = [t.strftime("%Y-%m-%d") for t in d3.index[d3[col] == 1]]
        key = f"a{k}:{a}:buy13"
        stored = R4["3d"].get(key)
        line = f"[3d a{k} {a}] {n} completions: {', '.join(dates)}"
        if stored is None:
            line += "  (not scored in R4: fewer than 6 completions)"
        say(line)
        entry = {"n": n, "dates": dates, "periods": [period_of(pd.Timestamp(x)) for x in dates]}
        if n >= 3:
            r = H2.event_test2(d3, (col, "raw", "top", 1), a, horizons=(1, 3, 5), freq="3d", lag=1)
            say("   " + fmt(r, (1, 3, 5)))
            entry["cells"] = cell_summary(r, (1, 3, 5))
            # pooled (all periods) mean excess vs full-sample mean, for the sign only
            px3 = H.price(d3, a)
            f3 = (d3[col] == 1).shift(1).fillna(False).astype(bool)
            for h in (1, 3, 5):
                fwd = px3.shift(-h) / px3 - 1
                m = fwd.notna()
                entry[f"pooled_excess_h{h}"] = float(fwd[m & f3].mean() - fwd[m].mean()) if (m & f3).sum() else None
            say("   pooled all-period excess (sign only): " + ", ".join(f"h={h} {entry[f'pooled_excess_h{h}'] * 100:+.2f}%" for h in (1, 3, 5) if entry.get(f"pooled_excess_h{h}") is not None))
        RES["three_day"][key] = entry

# ------------------------------------------------------------------ 7. placebo
say("\n==== 7. PLACEBO: random dates matched on count (5000 draws), and matched on count AND drawn from bottom-quintile ret20 bars ====")
RES["placebo"] = {}
rng = np.random.default_rng(20261119)
NDRAW = 5000
for a in ("btc", "eth"):
    px = H.price(d, a)
    flag = (d[f"td_buy13_{a}"] == 1).shift(1).fillna(False).astype(bool)
    downq = (d[f"ret20pct_{a}"] <= 0.2).shift(1).fillna(False).astype(bool)
    RES["placebo"][a] = {}
    for h in (3, 5):
        fwd = px.shift(-h) / px - 1
        pooled_obs = 0.0; pooled_rand = np.zeros(NDRAW); pooled_rand_dq = np.zeros(NDRAW); pooled_n = 0
        for per in ("train", "validation"):
            f, y, q = (H2.slice_period(x, per, "1d") for x in (flag, fwd, downq))
            m = y.notna()
            f, y, q = f[m], y[m], q[m]
            n = int(f.sum())
            if n < 3:
                continue
            obs = float(y[f].mean() - y.mean())
            yv = y.to_numpy(float); qidx = np.where(q.to_numpy())[0]
            rand = np.array([yv[rng.choice(len(yv), n, replace=False)].mean() - yv.mean() for _ in range(NDRAW)])
            rand_dq = np.array([yv[rng.choice(qidx, n, replace=False)].mean() - yv.mean() for _ in range(NDRAW)])
            p_all = float((rand <= obs).mean()); p_dq = float((rand_dq <= obs).mean())
            say(f"[{a}] h={h} {per}: observed excess {obs * 100:+.2f}% (n={n}); random-date placebo p(<=obs)={p_all:.3f} "
                f"[placebo mean {rand.mean() * 100:+.2f}%, sd {rand.std() * 100:.2f}%]; downtrend-matched placebo p(<=obs)={p_dq:.3f} "
                f"[placebo mean {rand_dq.mean() * 100:+.2f}%, sd {rand_dq.std() * 100:.2f}%]")
            RES["placebo"][a][f"{per}_h{h}"] = {"obs_excess": obs, "n": n, "p_random": p_all, "random_mean": float(rand.mean()), "random_sd": float(rand.std()),
                                                "p_downtrend_matched": p_dq, "downtrend_mean": float(rand_dq.mean()), "downtrend_sd": float(rand_dq.std())}
            # pooled train+validation (weighted by n) for one combined p
            pooled_obs += obs * n; pooled_rand += rand * n; pooled_rand_dq += rand_dq * n; pooled_n += n
        if pooled_n:
            po = pooled_obs / pooled_n; pr = pooled_rand / pooled_n; pq = pooled_rand_dq / pooled_n
            say(f"[{a}] h={h} train+validation pooled: observed {po * 100:+.2f}%, random p={float((pr <= po).mean()):.3f}, downtrend-matched p={float((pq <= po).mean()):.3f}")
            RES["placebo"][a][f"pooled_h{h}"] = {"obs_excess": po, "p_random": float((pr <= po).mean()), "p_downtrend_matched": float((pq <= po).mean())}

# ------------------------------------------------------------------ save
with open(os.path.join(OUT, "refute_td13.json"), "w") as fh:
    json.dump(RES, fh, indent=1, default=str)
with open(os.path.join(OUT, "refute_td13_stdout.txt"), "w") as fh:
    fh.write("\n".join(LINES))
say(f"\nwritten: {os.path.join(OUT, 'refute_td13.json')} and refute_td13_stdout.txt")
