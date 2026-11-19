"""Refutation of the pass-3 cell "ETH daily TD9 buy setup -> shallower 10-day drawdown" (R4 1d :eth:buy9 W=10).

Reads data/daily2.pkl, uses harness/harness2/harness3 unchanged. Writes results3/refute/refute_td9_eth.{json,txt}.
Tests: (1) reproduce, (2) lag 2, (3) validation episodes and leave-one-out, (4) perfected vs non-perfected,
(5) placebo of random dates matched on count per period (500 draws), (6) setup-count neighbours (6,7,8,9,10+),
(7) 10-day forward return check, (8) simpler control: trailing-decline bars that are NOT TD9 completions.
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
import harness3 as H3  # noqa: E402

LINES = []
OUT = {}


def say(*p):
    s = " ".join(str(x) for x in p)
    print(s, flush=True)
    LINES.append(s)


def cell_summary(res, W=10):
    """Compact per-period dict from a risk_test result."""
    e = res["windows"][W]
    out = {}
    for p in ("train", "validation", "test"):
        r = e["cell"].get(p, {})
        out[p] = {k: r.get(k) for k in ("n_flag", "n_ind", "mdd_flag", "mdd_all", "mdd_diff", "t_nw", "crash_lift", "crash_n", "missed_mean20", "false_alarm")}
    out["verdict"] = e["verdict"]
    return out


def fmt(res, W=10):
    return H2.risk_line({"windows": {W: res["windows"][W]}})


# ---------------------------------------------------------------- data (identical to score3.load_daily for TD columns)
d = pd.read_pickle(os.path.join(ROOT, "data", "daily2.pkl"))
for a in ("btc", "eth"):
    H3.td_columns(d, a)
px = H.price(d, "eth")
SPEC = ("td_buy9_eth", "raw", "top", 1)
W = 10
mdd10 = H2.forward_mdd(px, W)
fwd10 = px.shift(-10) / px - 1
fwd20 = px.shift(-20) / px - 1

say("=" * 100)
say("REFUTATION: ETH daily TD9 BUY setup completion -> shallower 10-day drawdown (R4 1d :eth:buy9, W=10)")
say("=" * 100)

# ---------------------------------------------------------------- (1) reproduce
say("\n(1) REPRODUCE  lag=1, W=10, crash -10%, episode bar 20")
r1 = H2.risk_test(d, SPEC, "eth", windows=(10, 20, 30), lag=1, crash=-0.10, episode_bar=20)
say(H2.risk_line(r1))
OUT["1_reproduce"] = {str(w): cell_summary(r1, w) for w in (10, 20, 30)}
ref = json.load(open(os.path.join(ROOT, "results3", "R4_td_sequential.json")))["1d"][":eth:buy9"]["risk"]["windows"]["10"]["cell"]
match = all(abs(ref[p]["mdd_diff"] - r1["windows"][10]["cell"][p]["mdd_diff"]) < 1e-12 and abs(ref[p]["t_nw"] - r1["windows"][10]["cell"][p]["t_nw"]) < 1e-9 for p in ("train", "validation", "test"))
say(f"   matches results3/R4_td_sequential.json to 1e-12: {match}")
OUT["1_reproduce"]["matches_stored_json"] = bool(match)

# ---------------------------------------------------------------- (2) lag 2
say("\n(2) LAG 2 (enter two bars after the 9th bar)")
r2 = H2.risk_test(d, SPEC, "eth", windows=(10,), lag=2, crash=-0.10, episode_bar=20)
say(fmt(r2))
OUT["2_lag2"] = cell_summary(r2)
say("    lag 0 (enter at the close of the 9th bar, for reference, not a tradable spec):")
r0 = H2.risk_test(d, SPEC, "eth", windows=(10,), lag=0, crash=-0.10, episode_bar=20)
say(fmt(r0))
OUT["2_lag0_reference"] = cell_summary(r0)

# ---------------------------------------------------------------- (3) validation episodes and leave-one-out
say("\n(3) THE VALIDATION EPISODES (lag 1: completion date t, entry at t+1, forward 10-day mdd and return from the entry bar)")
flag1, _ = H2.make_flag(d, SPEC, "1d", 1)
val_entries = H2.slice_period(flag1[flag1], "validation", "1d").index
tbl = []
for e in val_entries:
    comp = e - pd.Timedelta(days=1)
    row = {"completion": str(comp.date()), "entry": str(e.date()), "entry_close": float(px[e]),
           "mdd10": float(mdd10[e]), "fwd10": float(fwd10[e]), "fwd20": float(fwd20[e]),
           "trail9_ret": float(px[comp] / px.shift(9)[comp] - 1), "perfected": int(d.loc[comp, "td_buy9p_eth"]),
           "setup_count_next_day": int(d.loc[e, "td_setup_eth"])}
    tbl.append(row)
    say(f"   completion {row['completion']} entry {row['entry']}  close {row['entry_close']:.0f}  mdd10 {row['mdd10'] * 100:+.1f}%  fwd10 {row['fwd10'] * 100:+.1f}%  fwd20 {row['fwd20'] * 100:+.1f}%  trailing 9d {row['trail9_ret'] * 100:+.1f}%  perfected={row['perfected']}  count on entry day={row['setup_count_next_day']}")
va_all = H2.slice_period(mdd10, "validation", "1d")
say(f"   validation all-bar mean mdd10 {va_all.mean() * 100:+.2f}%, median {va_all.median() * 100:+.2f}%, share of bars with mdd10 >= 0 (no close below entry in 10 days): {(va_all >= 0).mean():.3f}")
OUT["3_validation_episodes"] = {"episodes": tbl, "val_mean_mdd10_all": float(va_all.mean()), "val_share_mdd10_nonneg": float((va_all >= 0).mean())}

# leave-one-out / leave-two-out on the completion dates (zero the signal column at the completion date)
say("   leave-out on validation (best episode = largest mdd10; also drop each one in turn, then best 2, then best 3):")
loo = {}
order = sorted(tbl, key=lambda r: -r["mdd10"])
def run_dropping(drop_completions, label):
    d2 = d.copy()
    for c in drop_completions:
        d2.loc[pd.Timestamp(c), "td_buy9_eth"] = 0.0
    rr = H2.risk_test(d2, SPEC, "eth", windows=(10,), lag=1, crash=-0.10, episode_bar=20)
    say(f"   [{label}] " + fmt(rr))
    return cell_summary(rr)
for r in tbl:
    loo[f"drop_{r['completion']}"] = run_dropping([r["completion"]], f"drop {r['completion']}")
loo["drop_best2"] = run_dropping([order[0]["completion"], order[1]["completion"]], f"drop best 2 ({order[0]['completion']}, {order[1]['completion']})")
loo["drop_best3"] = run_dropping([o["completion"] for o in order[:3]], "drop best 3 (leaves 1 bar: insufficient by construction)")
OUT["3_leave_out"] = loo

# ---------------------------------------------------------------- (4) perfected vs non-perfected
say("\n(4) PERFECTED (td_buy9p_eth, closes-based) vs NON-PERFECTED (buy9 & ~buy9p) at W=10, lag 1")
rp = H2.risk_test(d, ("td_buy9p_eth", "raw", "top", 1), "eth", windows=(10,), lag=1, crash=-0.10, episode_bar=20)
say("   perfected:     " + fmt(rp))
d["td_buy9np_eth"] = ((d["td_buy9_eth"] > 0) & (d["td_buy9p_eth"] == 0)).astype(float)
rnp = H2.risk_test(d, ("td_buy9np_eth", "raw", "top", 1), "eth", windows=(10,), lag=1, crash=-0.10, episode_bar=20)
say("   non-perfected: " + fmt(rnp))
say(f"   counts: buy9 {int(d['td_buy9_eth'].sum())}, perfected {int(d['td_buy9p_eth'].sum())}, non-perfected {int(d['td_buy9np_eth'].sum())}")
OUT["4_perfected"] = {"perfected": cell_summary(rp), "non_perfected": cell_summary(rnp),
                     "n": {"buy9": int(d["td_buy9_eth"].sum()), "perfected": int(d["td_buy9p_eth"].sum()), "non_perfected": int(d["td_buy9np_eth"].sum())}}

# ---------------------------------------------------------------- (5) placebo
say("\n(5) PLACEBO: random entry dates matched on count per period (train 21 / validation 4 / test 3), 500 draws, seed 20261119")
rng = np.random.default_rng(20261119)
n_per = {p: int(r1["windows"][10]["cell"][p]["n_flag"]) for p in ("train", "validation", "test")}
crash = -0.10
pools = {}
for p in ("train", "validation", "test"):
    dd = H2.slice_period(mdd10, p, "1d").dropna()
    pools[p] = dd
real = r1["windows"][10]["cell"]
val_t_real = real["validation"]["t_nw"]
N = 500
cnt = {"val_t_ge_4p9": 0, "val_t_ge_2p5": 0, "all_pos": 0, "val_t_ge_4p9_and_all_pos": 0, "val_t_ge_2p5_and_all_pos": 0, "full_pass_rule": 0,
       "val_diff_ge_real": 0, "val_all4_nonneg": 0}
val_ts = []
for k in range(N):
    diffs, ts, lifts, miss = {}, {}, {}, {}
    for p in ("train", "validation", "test"):
        dd = pools[p]
        idx = rng.choice(len(dd), size=n_per[p], replace=False)
        f = np.zeros(len(dd)); f[idx] = 1
        y = dd.to_numpy(float)
        diffs[p] = float(y[idx].mean() - y.mean())
        ts[p], _ = H.nw_t(y, f, W)
        ev = y <= crash
        base = ev.mean()
        lifts[p] = float(ev[idx].mean() / base) if base else None
        r20 = H2.slice_period(fwd20, p, "1d").reindex(dd.index).to_numpy(float)[idx]
        miss[p] = float(np.nanmean(r20)) if np.isfinite(r20).any() else 0.0
        if p == "validation":
            val_ts.append(ts[p]); val_all_nonneg = bool((y[idx] >= 0).all())
    all_pos = all(diffs[p] > 0 for p in diffs)
    tv = ts["validation"]
    cnt["val_t_ge_4p9"] += tv >= 4.9
    cnt["val_t_ge_2p5"] += tv >= 2.5
    cnt["all_pos"] += all_pos
    cnt["val_t_ge_4p9_and_all_pos"] += (tv >= 4.9) and all_pos
    cnt["val_t_ge_2p5_and_all_pos"] += (tv >= 2.5) and all_pos
    cnt["val_diff_ge_real"] += diffs["validation"] >= real["validation"]["mdd_diff"]
    cnt["val_all4_nonneg"] += val_all_nonneg
    full = all_pos and tv >= 2.5 and lifts["validation"] is not None and lifts["validation"] <= 0.6 and lifts["test"] is not None and lifts["test"] <= 0.8 and miss["validation"] > 0
    cnt["full_pass_rule"] += full
val_ts = np.array(val_ts)
say(f"   validation t distribution over {N} draws (n_flag=4): mean {np.nanmean(val_ts):+.2f}, sd {np.nanstd(val_ts):.2f}, p95 {np.nanpercentile(val_ts, 95):+.2f}, p99 {np.nanpercentile(val_ts, 99):+.2f}, max {np.nanmax(val_ts):+.2f}")
for k, v in cnt.items():
    say(f"   {k:32s} {v:4d}/{N}  = {v / N:.3f}")
say(f"   real: validation mdd_diff {real['validation']['mdd_diff'] * 100:+.2f} t {val_t_real:.2f}; signs train/val/test all positive")
OUT["5_placebo"] = {"draws": N, "seed": 20261119, "n_per_period": n_per, "counts": {k: int(v) for k, v in cnt.items()}, "rates": {k: v / N for k, v in cnt.items()},
                    "val_t_dist": {"mean": float(np.nanmean(val_ts)), "sd": float(np.nanstd(val_ts)), "p95": float(np.nanpercentile(val_ts, 95)), "p99": float(np.nanpercentile(val_ts, 99)), "max": float(np.nanmax(val_ts))}}

# second placebo: random dates drawn ONLY from bars that are not TD9 completions but share the trailing-decline state
# (trailing 9-day return in the same range as the real completions) -> is "price fell for a while" enough?
say("   placebo B: random dates matched on count AND on trailing 9-day return <= the 75th percentile of the real completions' trailing returns (same draws, 500)")
trail9 = px / px.shift(9) - 1
comp_all = d.index[d["td_buy9_eth"] > 0]
thr_trail = float(trail9[comp_all].quantile(0.75))
say(f"   trailing-9d return of real completions: median {trail9[comp_all].median() * 100:+.1f}%, p75 {thr_trail * 100:+.1f}%")
elig = (trail9.shift(1) <= thr_trail) & (d["td_buy9_eth"].shift(1).fillna(0) == 0)
cntB = {"val_t_ge_4p9": 0, "val_t_ge_2p5_and_all_pos": 0, "all_pos": 0, "val_diff_ge_real": 0}
poolsB = {p: H2.slice_period(mdd10[elig], p, "1d").dropna() for p in ("train", "validation", "test")}
say("   eligible bars per period: " + ", ".join(f"{p} {len(poolsB[p])}" for p in poolsB))
for k in range(N):
    diffs, ts = {}, {}
    for p in ("train", "validation", "test"):
        dd, full = poolsB[p], pools[p]
        idx = rng.choice(len(dd), size=n_per[p], replace=False)
        chosen = dd.index[idx]
        f = full.index.isin(chosen).astype(float)
        y = full.to_numpy(float)
        diffs[p] = float(y[f == 1].mean() - y.mean())
        ts[p], _ = H.nw_t(y, f, W)
    all_pos = all(v > 0 for v in diffs.values())
    cntB["val_t_ge_4p9"] += ts["validation"] >= 4.9
    cntB["val_t_ge_2p5_and_all_pos"] += (ts["validation"] >= 2.5) and all_pos
    cntB["all_pos"] += all_pos
    cntB["val_diff_ge_real"] += diffs["validation"] >= real["validation"]["mdd_diff"]
for k, v in cntB.items():
    say(f"   B {k:30s} {v:4d}/{N}  = {v / N:.3f}")
OUT["5_placebo_B_trailing_decline"] = {"thr_trail9": thr_trail, "eligible": {p: int(len(poolsB[p])) for p in poolsB}, "counts": {k: int(v) for k, v in cntB.items()}, "rates": {k: v / N for k, v in cntB.items()}}

# ---------------------------------------------------------------- (6) setup-count neighbours
say("\n(6) FLAG = k-th BAR OF THE BUY SETUP (td_setup_eth == -k on day t, entry t+1), W=10. 9 is the original cell; 10+ = count ran past 9")
nb = {}
for k in (5, 6, 7, 8, 9, 10):
    col = f"td_buyk{k}_eth"
    if k < 10:
        d[col] = (d["td_setup_eth"] == -k).astype(float)
    else:
        d[col] = (d["td_setup_eth"] <= -10).astype(float)
    rk = H2.risk_test(d, (col, "raw", "top", 1), "eth", windows=(10,), lag=1, crash=-0.10, episode_bar=20)
    say(f"   count {'>=10' if k == 10 else k}: n={int(d[col].sum())}  " + fmt(rk))
    nb[str(k)] = cell_summary(rk)
    nb[str(k)]["n_total"] = int(d[col].sum())
d["td_buy_ge7_eth"] = (d["td_setup_eth"] <= -7).astype(float)
rk = H2.risk_test(d, ("td_buy_ge7_eth", "raw", "top", 1), "eth", windows=(10,), lag=1, crash=-0.10, episode_bar=20)
say(f"   any count >= 7 (state, not event): n={int(d['td_buy_ge7_eth'].sum())}  " + fmt(rk))
nb["ge7_state"] = cell_summary(rk)
d["td_buy8only_eth"] = ((d["td_setup_eth"] == -8) & (d["td_setup_eth"].shift(-1) != -9)).astype(float)  # uses t+1 info: diagnostic only
say(f"   (diagnostic, uses next-day info) 8th bar that did NOT go on to a 9: n={int(d['td_buy8only_eth'].sum())}  " + fmt(H2.risk_test(d, ("td_buy8only_eth", "raw", "top", 1), "eth", windows=(10,), lag=1, crash=-0.10, episode_bar=20)))
OUT["6_setup_count_neighbours"] = nb

# ---------------------------------------------------------------- (7) return check
say("\n(7) RETURN CHECK: 10-day forward return on flagged entry bars (lag 1) per period, raw mean, period mean, excess, hit rate; also 20-day")
rr = H2.event_test2(d, SPEC, "eth", horizons=(10, 20), lag=1, episode_bar=30)
say(H2.line2(rr))
retc = {}
for h in (10, 20):
    retc[str(h)] = {}
    for p in ("train", "validation", "test"):
        c = rr["horizons"][h]["cell"][p]
        retc[str(h)][p] = {k: c.get(k) for k in ("n_flag", "n_ind", "mean_flag", "mean_all", "excess", "hit", "t_nw", "net")}
        say(f"   h={h} {p:10s} n={c['n_flag']:2d} ind={c['n_ind']:2d} mean_flag {c['mean_flag'] * 100:+.2f}%  mean_all {c['mean_all'] * 100:+.2f}%  excess {c['excess'] * 100:+.2f}%  hit {c['hit']:.2f}  t {c['t_nw']:+.2f}")
OUT["7_return_check"] = retc

# ---------------------------------------------------------------- (8) simpler control: trailing decline without TD9
say("\n(8) SIMPLER CONTROL: bars whose trailing 9-day return is <= the real completions' p75 but that are NOT TD9 completions (state flag), W=10, lag 1")
d["ctrl_decline_eth"] = ((trail9 <= thr_trail) & (d["td_buy9_eth"] == 0)).astype(float)
rc = H2.risk_test(d, ("ctrl_decline_eth", "raw", "top", 1), "eth", windows=(10,), lag=1, crash=-0.10, episode_bar=20)
say(f"   decline-not-TD9: n={int(d['ctrl_decline_eth'].sum())}  " + fmt(rc))
OUT["8_control_trailing_decline"] = cell_summary(rc)
# and the decile of trailing 9-day return
d["ctrl_trail9_eth"] = trail9
rc2 = H2.risk_test(d, ("ctrl_trail9_eth", "pct365", "bottom", 0.1), "eth", windows=(10,), lag=1, crash=-0.10, episode_bar=20)
say("   trailing 9d return bottom decile (pct365): " + fmt(rc2))
OUT["8_control_trail9_bottom_decile"] = cell_summary(rc2)

# ---------------------------------------------------------------- (9) BTC same cell and ex-2020 train for the record
say("\n(9) FOR THE RECORD: BTC buy9 W=10 lag 1; ETH train ex-2020")
rb = H2.risk_test(d, ("td_buy9_btc", "raw", "top", 1), "btc", windows=(10,), lag=1, crash=-0.10, episode_bar=20)
say("   btc buy9: " + fmt(rb))
d_ex = d[(d.index < "2020-01-01") | (d.index > "2020-12-31")]
rx = H2.risk_test(d_ex, SPEC, "eth", windows=(10,), lag=1, crash=-0.10, episode_bar=20)
say("   eth buy9 ex-2020: " + fmt(rx))
OUT["9_btc_and_ex2020"] = {"btc_buy9": cell_summary(rb), "eth_ex2020": cell_summary(rx)}

# ---------------------------------------------------------------- write
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

with open(os.path.join(HERE, "refute_td9_eth.json"), "w") as fh:
    json.dump(clean(OUT), fh, indent=1)
with open(os.path.join(HERE, "refute_td9_eth.txt"), "w") as fh:
    fh.write("\n".join(LINES) + "\n")
say(f"\nwritten: {os.path.join(HERE, 'refute_td9_eth.json')} and .txt")
