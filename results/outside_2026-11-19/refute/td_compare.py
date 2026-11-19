"""Compare the independent TD Sequential implementation with harness3.td_sequential.

Steps 2-5 of the refutation task. Writes results3/refute/td_compare.json and prints a report.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RESEARCH = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, RESEARCH)
sys.path.insert(0, HERE)
import harness as H  # noqa: E402
import harness2 as H2  # noqa: E402
import harness3 as H3  # noqa: E402
from td_independent import td_sequential_independent as td_ind  # noqa: E402

FLAGS = ("buy9", "sell9", "buy9p", "sell9p", "buy13", "sell13")
OUT = {}


def say(*a):
    print(*a, flush=True)


def flags_of(df):
    return {k: df[k].astype(bool) for k in FLAGS}


def compare(a_flags, b_flags, label):
    """a = harness3, b = independent. Returns dict of counts and differing dates per flag."""
    res = {}
    for k in FLAGS:
        fa, fb = a_flags[k], b_flags[k]
        only_a = list(map(str, fa.index[fa & ~fb]))
        only_b = list(map(str, fb.index[fb & ~fa]))
        res[k] = {"n_harness3": int(fa.sum()), "n_independent": int(fb.sum()), "only_harness3": only_a,
                  "only_independent": only_b}
        tag = "IDENTICAL" if not only_a and not only_b else f"DIFF h3-only={len(only_a)} ind-only={len(only_b)}"
        say(f"  [{label}] {k:7s} harness3 {int(fa.sum()):4d} independent {int(fb.sum()):4d} -> {tag}")
        for dte in only_a[:10]:
            say(f"       only harness3   : {dte}")
        for dte in only_b[:10]:
            say(f"       only independent: {dte}")
    return res


def period_of(ts):
    ts = pd.Timestamp(ts)
    if ts <= pd.Timestamp("2024-06-30"):
        return "train"
    if ts <= pd.Timestamp("2025-12-31"):
        return "validation"
    return "test"


# =====================================================================================================
# Step 2: daily flag-by-flag comparison
# =====================================================================================================
say("==== STEP 2: daily flag-by-flag comparison, data/daily2.pkl ====")
d = pd.read_pickle(os.path.join(RESEARCH, "data", "daily2.pkl"))
OUT["daily"] = {}
for a in ("btc", "eth"):
    h3 = H3.td_sequential(d[a])
    ind = td_ind(d[a])
    res = compare(flags_of(h3), flags_of(ind), f"1D {a}")
    # setup count column: harness3 setup = +sell_count / -buy_count
    my_signed = np.where(ind["sell_count"] > 0, ind["sell_count"], -ind["buy_count"]).astype(float)
    n_setup_diff = int((h3["setup"].to_numpy() != my_signed).sum())
    say(f"  [1D {a}] signed setup-count column differs on {n_setup_diff} bars")
    res["setup_count_diff_bars"] = n_setup_diff
    # completion dates by period (for the record)
    res["completion_dates"] = {k: {p: [str(x.date()) for x in ind.index[ind[k]] if period_of(x) == p]
                                   for p in ("train", "validation", "test")} for k in FLAGS}
    OUT["daily"][a] = res

# 3D anchors as scored by score3 (every third bar) -- same comparison
say("\n==== STEP 2b: 3D anchors (every third daily bar), flag-by-flag ====")
OUT["3d"] = {}
for anchor in (0, 1, 2):
    d3 = d.iloc[anchor::3]
    for a in ("btc", "eth"):
        h3 = H3.td_sequential(d3[a])
        ind = td_ind(d3[a])
        res = compare(flags_of(h3), flags_of(ind), f"3D-a{anchor} {a}")
        OUT["3d"][f"a{anchor}:{a}"] = {k: {kk: v for kk, v in res[k].items() if kk.startswith("n_")} | {
            "n_diff": len(res[k]["only_harness3"]) + len(res[k]["only_independent"])} for k in FLAGS}

# =====================================================================================================
# Step 3a: definition-ambiguity switches (what changes if the definition is read the other way)
# =====================================================================================================
say("\n==== STEP 3a: sensitivity to the two points the definition leaves open (daily) ====")
OUT["variants"] = {}
for a in ("btc", "eth"):
    base = td_ind(d[a])
    v_cd10 = td_ind(d[a], countdown_from_bar9=False)      # countdown starts on bar after completion
    v_reset = td_ind(d[a], setup_reset_after_9=True)       # setup count restarts after bar 9 (18 -> two 9s)
    for name, v in (("countdown_starts_bar10", v_cd10), ("setup_resets_after_9", v_reset)):
        row = {}
        for k in FLAGS:
            fb, fv = base[k].astype(bool), v[k].astype(bool)
            moved = sorted(set(map(str, fb.index[fb != fv].date)))
            row[k] = {"n_base": int(fb.sum()), "n_variant": int(fv.sum()), "n_bars_changed": int((fb != fv).sum()),
                      "changed_dates": moved}
        OUT["variants"][f"{a}:{name}"] = row
        say(f"  [{a}] {name}: " + ", ".join(f"{k} {row[k]['n_base']}->{row[k]['n_variant']} ({row[k]['n_bars_changed']} bars moved)" for k in FLAGS))
    # long runs (>= 18) that would double-count under the reset variant
    runs_b = base["buy_count"]; runs_s = base["sell_count"]
    say(f"  [{a}] max consecutive buy-setup bars {int(runs_b.max())}, sell {int(runs_s.max())}; "
        f"bars with count>=18: buy {int((runs_b >= 18).sum())}, sell {int((runs_s >= 18).sum())}")

# =====================================================================================================
# Step 3b: the one passing cell -- ETH buy9, risk W=10 -- episode by episode
# =====================================================================================================
say("\n==== STEP 3b: ETH buy9 risk W=10 (the only PASS in R4) reproduced episode by episode ====")
H3.td_columns(d, "eth")
H3.td_columns(d, "btc")
r = H2.risk_test(d, ("td_buy9_eth", "raw", "top", 1), "eth", windows=(10,), freq="1d", lag=1, crash=-0.10, episode_bar=20)
cell = r["windows"][10]["cell"]
say("  harness2 risk_test W=10:", {p: {k: cell[p].get(k) for k in ("n_flag", "n_ind", "mdd_flag", "mdd_all", "mdd_diff", "t_nw", "crash_n")} for p in cell})
say("  verdict:", r["windows"][10]["verdict"])
px = d["eth"]
mdd10 = H2.forward_mdd(px, 10)
flag, _ = H2.make_flag(d, ("td_buy9_eth", "raw", "top", 1), "1d", 1)
episodes = {}
for p in ("train", "validation", "test"):
    f = H2.slice_period(flag, p, "1d"); m = H2.slice_period(mdd10, p, "1d")
    ok = f & m.notna()
    rows = [{"entry_date": str(ts.date()), "completion_date": str((ts - pd.Timedelta(days=1)).date()),
             "fwd_mdd10": float(m[ts]), "fwd_ret10": float(px.shift(-10)[ts] / px[ts] - 1)} for ts in f.index[ok]]
    episodes[p] = rows
    say(f"  {p}: mdd_all {float(m[m.notna()].mean())*100:+.2f}%  flagged entries:")
    for row in rows:
        say(f"     entry {row['entry_date']} (buy9 on {row['completion_date']}): fwd mdd10 {row['fwd_mdd10']*100:+.2f}%  fwd ret10 {row['fwd_ret10']*100:+.2f}%")
# leave-one-out on validation
val_f = H2.slice_period(flag, "validation", "1d"); val_m = H2.slice_period(mdd10, "validation", "1d")
m_ok = val_m.notna() & val_f.notna()
loo = {}
for ts in val_f.index[val_f & m_ok]:
    f2 = val_f.copy(); f2[ts] = False
    t, _ = H.nw_t(val_m[m_ok].to_numpy(float), f2[m_ok].to_numpy(float), 10)
    diff = float(val_m[m_ok][f2[m_ok]].mean() - val_m[m_ok].mean())
    loo[str(ts.date())] = {"mdd_diff_without": diff, "t_without": float(t)}
    say(f"  validation leave-one-out drop {ts.date()}: mdd_diff {diff*100:+.2f}% t={t:.2f}")
# alternative: lag=2 and the buy9p variant required by PREREG3 ('non-perfected and perfected agree in sign')
r2 = H2.risk_test(d, ("td_buy9_eth", "raw", "top", 1), "eth", windows=(10,), freq="1d", lag=2, crash=-0.10, episode_bar=20)
rp = H2.risk_test(d, ("td_buy9p_eth", "raw", "top", 1), "eth", windows=(10,), freq="1d", lag=1, crash=-0.10, episode_bar=20)
rb = H2.risk_test(d, ("td_buy9_btc", "raw", "top", 1), "btc", windows=(10,), freq="1d", lag=1, crash=-0.10, episode_bar=20)
def fmt_cell(p, c):
    if c.get("mdd_diff") is None:
        return "%s n<3" % p[:3]
    return "%s mdd_diff %+.2f%% t=%.2f n=%d n_ind=%d" % (p[:3], c["mdd_diff"] * 100, c["t_nw"], c["n_flag"], c["n_ind"])


for name, rr in (("eth buy9 lag=2", r2), ("eth buy9p lag=1", rp), ("btc buy9 lag=1", rb)):
    c = rr["windows"][10]["cell"]
    say("  %s W=10: " % name + " | ".join(fmt_cell(p, c[p]) for p in c))
    say("     verdict: %s" % rr["windows"][10]["verdict"])
OUT["eth_buy9_W10"] = {"cell": {p: {k: cell[p].get(k) for k in ("n_flag", "n_ind", "mdd_flag", "mdd_all", "mdd_diff", "t_nw", "crash_n", "crash_lift")} for p in cell},
                       "verdict": r["windows"][10]["verdict"], "episodes": episodes, "validation_leave_one_out": loo,
                       "lag2_cell": {p: {k: r2["windows"][10]["cell"][p].get(k) for k in ("n_flag", "n_ind", "mdd_diff", "t_nw")} for p in r2["windows"][10]["cell"]},
                       "lag2_verdict": r2["windows"][10]["verdict"],
                       "buy9p_cell": {p: {k: rp["windows"][10]["cell"][p].get(k) for k in ("n_flag", "n_ind", "mdd_diff", "t_nw")} for p in rp["windows"][10]["cell"]},
                       "buy9p_verdict": rp["windows"][10]["verdict"],
                       "btc_buy9_cell": {p: {k: rb["windows"][10]["cell"][p].get(k) for k in ("n_flag", "n_ind", "mdd_diff", "t_nw")} for p in rb["windows"][10]["cell"]},
                       "btc_buy9_verdict": rb["windows"][10]["verdict"]}

# =====================================================================================================
# Step 4: random walk sanity check
# =====================================================================================================
say("\n==== STEP 4: pure random walk, 3000 bars, completions per 1000 bars ====")
rng = np.random.default_rng(20261119)
N_SEEDS = 200
rates = {"h3": {k: [] for k in FLAGS}, "ind": {k: [] for k in FLAGS}}
n_disagree = {k: 0 for k in FLAGS}
for seed in range(N_SEEDS):
    rw = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.02, 3000))), index=pd.RangeIndex(3000))
    h3 = H3.td_sequential(rw); ind = td_ind(rw)
    for k in FLAGS:
        rates["h3"][k].append(h3[k].sum() / 3.0)
        rates["ind"][k].append(ind[k].sum() / 3.0)
        n_disagree[k] += int((h3[k].astype(bool) != ind[k].astype(bool)).sum())
summary = {}
for k in FLAGS:
    a1, a2 = np.array(rates["h3"][k]), np.array(rates["ind"][k])
    summary[k] = {"harness3_per_1000_mean": float(a1.mean()), "harness3_per_1000_sd": float(a1.std()),
                  "independent_per_1000_mean": float(a2.mean()), "independent_per_1000_sd": float(a2.std()),
                  "bars_disagreeing_total": n_disagree[k]}
    say(f"  {k:7s} harness3 {a1.mean():6.2f} +/- {a1.std():4.2f} per 1000 bars | independent {a2.mean():6.2f} +/- {a2.std():4.2f} | disagreeing bars over {N_SEEDS} seeds: {n_disagree[k]}")
# compare to the real data rate (daily 2878 bars)
for a in ("btc", "eth"):
    say(f"  real daily {a}: " + ", ".join(f"{k} {OUT['daily'][a][k]['n_independent'] / len(d) * 1000:.2f}/1000" for k in FLAGS))
# Gaussian iid noise around a constant (no drift, mean-reverting) for contrast
rates_wn = {k: [] for k in ("buy9", "sell9")}
for seed in range(50):
    wn = pd.Series(100 + rng.normal(0, 1, 3000))
    ind = td_ind(wn)
    for k in rates_wn:
        rates_wn[k].append(ind[k].sum() / 3.0)
say(f"  contrast, iid white noise around a constant: buy9 {np.mean(rates_wn['buy9']):.3f}/1000, sell9 {np.mean(rates_wn['sell9']):.3f}/1000 (2^-9*1000 = {1000/512:.2f} would be the independent-coin rate)")
OUT["random_walk"] = {"n_seeds": N_SEEDS, "bars": 3000, "sigma_per_bar": 0.02, "flags": summary,
                      "white_noise_buy9_per_1000": float(np.mean(rates_wn["buy9"])), "white_noise_sell9_per_1000": float(np.mean(rates_wn["sell9"])),
                      "real_daily_per_1000": {a: {k: OUT["daily"][a][k]["n_independent"] / len(d) * 1000 for k in FLAGS} for a in ("btc", "eth")}}

# =====================================================================================================
# Step 5: hourly NaN gaps
# =====================================================================================================
say("\n==== STEP 5: hourly BTC gaps (data/hourly.pkl) ====")
h = pd.read_pickle(os.path.join(RESEARCH, "data", "hourly.pkl"))
s = h["btc"]
na = s.isna()
say(f"  hourly rows {len(s)}, NaN closes {int(na.sum())}, gap runs {int((na & ~na.shift(1, fill_value=False)).sum())}")

# 5a: harness3 on dropna'd vs independent on dropna'd (what score3 actually does)
px = s.dropna()
h3_skip = H3.td_sequential(px); ind_skip = td_ind(px)
say("  5a. gaps skipped (score3 behaviour), harness3 vs independent on the dropna'd series:")
res5a = compare(flags_of(h3_skip), flags_of(ind_skip), "1H btc skip")

# 5b: harness3 on the full series (NaN resets the count) and on ffill
h3_reset = H3.td_sequential(s)
ind_reset = td_ind(s)
say("  5b. gaps as NaN in place (count resets at a gap), harness3 vs independent:")
res5b = compare(flags_of(h3_reset), flags_of(ind_reset), "1H btc nan-reset")
h3_ffill = H3.td_sequential(s.ffill())

# how many skip-mode completions have a gap inside their 13-bar window (9 setup bars + 4 lookback)?
pos_in_full = pd.Series(np.arange(len(s)), index=s.index)
p_avail = pos_in_full[px.index].to_numpy()          # full-index positions of the available bars
span = np.full(len(px), np.nan)
span[12:] = p_avail[12:] - p_avail[:-12]            # hours covered by the last 13 available bars
has_gap = pd.Series(span > 12, index=px.index)      # > 12 hours means at least one NaN hour inside the window
base_rate = float(has_gap[12:].mean())
tbl = {}
for k in ("buy9", "sell9", "buy9p", "sell9p"):
    fk = h3_skip[k].astype(bool)
    n_k = int(fk.sum()); n_gap = int((fk & has_gap).sum())
    tbl[k] = {"n": n_k, "n_window_contains_gap": n_gap, "share": n_gap / n_k if n_k else None, "base_share_all_bars": base_rate}
    say(f"  skip-mode {k}: {n_k} completions, {n_gap} ({100*n_gap/max(n_k,1):.1f}%) have a gap inside the 13-bar window; "
        f"{100*base_rate:.1f}% of all bars do")
counts_modes = {m: {k: int(f[k].sum()) for k in FLAGS} for m, f in (("skip", h3_skip), ("nan_reset", h3_reset), ("ffill", h3_ffill))}
say("  completions by gap mode (harness3): " + json.dumps(counts_modes))
OUT["hourly"] = {"n_rows": len(s), "n_nan": int(na.sum()), "skip_h3_vs_ind": {k: {kk: v for kk, v in res5a[k].items() if kk.startswith('n_')} | {"n_diff": len(res5a[k]["only_harness3"]) + len(res5a[k]["only_independent"])} for k in FLAGS},
                 "nan_reset_h3_vs_ind": {k: {kk: v for kk, v in res5b[k].items() if kk.startswith('n_')} | {"n_diff": len(res5b[k]["only_harness3"]) + len(res5b[k]["only_independent"]), "only_h3": res5b[k]["only_harness3"][:20], "only_ind": res5b[k]["only_independent"][:20]} for k in FLAGS},
                 "skip_mode_gap_in_window": tbl, "counts_by_mode": counts_modes}

# 5c: synthetic ground truth. Take the gap-free tail of real BTC hourly (after the last gap) and transplant the
#     real gap mask onto it; compute the truth on the complete series and compare the three gap treatments.
say("  5c. ground-truth test: real gap mask transplanted onto the gap-free tail of BTC hourly")
last_gap_end = s.index[na][-1]
tail = s[s.index > last_gap_end]
mask_src = na[(na.index >= "2024-11-17") & (na.index <= last_gap_end)].to_numpy()
L = min(len(tail), len(mask_src))
tail = tail.iloc[:L]; mask = mask_src[:L]
say(f"  tail {tail.index[0]}..{tail.index[-1]} ({L} bars, NaN in tail: {int(tail.isna().sum())}); transplanted NaN hours {int(mask.sum())}")
truth = H3.td_sequential(tail)
gapped = tail.copy(); gapped[mask] = np.nan


def eval_modes(full, gapped, truth, label, near=16):
    """Compare each gap treatment to the truth computed on the complete series."""
    out = {}
    pos_gap = np.where(gapped.isna().to_numpy())[0]
    near_gap = np.zeros(len(full), dtype=bool)
    for p in pos_gap:
        near_gap[max(0, p - near):min(len(full), p + near + 1)] = True
    modes = {"skip": H3.td_sequential(gapped.dropna()).reindex(full.index).fillna(0.0),
             "nan_reset": H3.td_sequential(gapped),
             "ffill": H3.td_sequential(gapped.ffill())}
    for m, f in modes.items():
        row = {}
        for k in ("buy9", "sell9", "buy13", "sell13"):
            t = truth[k].astype(bool).to_numpy(); g = f[k].astype(bool).to_numpy()
            # a completion in the gapped series counts as 'matched' if truth has the same flag within +/-2 bars
            tw = pd.Series(t).rolling(5, center=True, min_periods=1).max().to_numpy().astype(bool)
            gw = pd.Series(g).rolling(5, center=True, min_periods=1).max().to_numpy().astype(bool)
            false_pos = int((g & ~tw).sum()); missed = int((t & ~gw).sum())
            row[k] = {"truth": int(t.sum()), "mode": int(g.sum()), "false_completions": false_pos, "missed_completions": missed,
                      "false_near_gap": int((g & ~tw & near_gap).sum()), "truth_near_gap": int((t & near_gap).sum())}
        out[m] = row
        say(f"   [{label}] {m:9s}: " + " | ".join(f"{k} truth {row[k]['truth']} got {row[k]['mode']} false {row[k]['false_completions']} (near gap {row[k]['false_near_gap']}) missed {row[k]['missed_completions']}" for k in row))
    out["share_bars_near_gap"] = float(near_gap.mean())
    say(f"   [{label}] share of bars within {near} h of a gap: {near_gap.mean()*100:.1f}%")
    return out


OUT["hourly"]["ground_truth_real_tail"] = eval_modes(tail, gapped, truth, "real tail")

# same with random walks carrying the same gap mask
say("  5d. same gap mask on random-walk hourly series (20 seeds, aggregated)")
agg = {m: {k: {"truth": 0, "mode": 0, "false_completions": 0, "missed_completions": 0, "false_near_gap": 0, "truth_near_gap": 0} for k in ("buy9", "sell9", "buy13", "sell13")} for m in ("skip", "nan_reset", "ffill")}
for seed in range(20):
    rw = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.004, L))), index=tail.index)
    tr = H3.td_sequential(rw)
    g = rw.copy(); g[mask] = np.nan
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        res = eval_modes(rw, g, tr, f"rw{seed}")
    for m in agg:
        for k in agg[m]:
            for kk in agg[m][k]:
                agg[m][k][kk] += res[m][k][kk]
for m in agg:
    say(f"   [rw x20] {m:9s}: " + " | ".join(f"{k} truth {agg[m][k]['truth']} got {agg[m][k]['mode']} false {agg[m][k]['false_completions']} (near gap {agg[m][k]['false_near_gap']}) missed {agg[m][k]['missed_completions']}" for k in agg[m]))
OUT["hourly"]["ground_truth_random_walk_x20"] = agg

# 4H resample: NaN 4h bars after resample('4h').last()
h4 = h.resample("4h").last()
say(f"  4H frame: rows {len(h4)}, NaN btc closes after resample().last(): {int(h4['btc'].isna().sum())} (dropped by score3 before TD)")
OUT["hourly"]["h4_nan_bars"] = int(h4["btc"].isna().sum())

with open(os.path.join(HERE, "td_compare.json"), "w") as fh:
    json.dump(OUT, fh, indent=1, default=str)
say("\nwrote", os.path.join(HERE, "td_compare.json"))
