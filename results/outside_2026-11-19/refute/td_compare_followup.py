"""Follow-ups: (a) mechanism of the single buy13 difference in NaN-in-place mode, (b) gap ground-truth with a
looser matching tolerance, split into timing shifts vs fabricated/missed setups, (c) 4H frame comparison,
(d) where the 1H flags fall relative to the gapped window."""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RESEARCH = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, RESEARCH)
sys.path.insert(0, HERE)
import harness3 as H3  # noqa: E402
from td_independent import td_sequential_independent as td_ind  # noqa: E402

FLAGS = ("buy9", "sell9", "buy9p", "sell9p", "buy13", "sell13")
OUT = {}


def say(*a):
    print(*a, flush=True)


h = pd.read_pickle(os.path.join(RESEARCH, "data", "hourly.pkl"))
s = h["btc"]

# (a) mechanism of the buy13 difference in NaN-in-place mode -------------------------------------------------
say("==== (a) buy13 difference, NaN-in-place mode, BTC 1H ====")
h3 = H3.td_sequential(s)
ind = td_ind(s)
# find the setup that started this countdown: last buy9 before 2024-12-05 05:00
t_ind = pd.Timestamp("2024-12-05 05:00"); t_h3 = pd.Timestamp("2024-12-08 09:00")
b9 = h3.index[(h3["buy9"] > 0) & (h3.index < t_ind)]
start = b9[-1]
say(f"  countdown started by buy9 at {start}; independent completes 13 at {t_ind}, harness3 at {t_h3}")
win = s[start:t_h3]
c = win.to_numpy(); idx = win.index
rows = []
for i in range(len(c)):
    ts = idx[i]
    pos = s.index.get_loc(ts)
    c_i, c_2, c_4 = s.iloc[pos], s.iloc[pos - 2], s.iloc[pos - 4]
    cond = (not np.isnan(c_i)) and (not np.isnan(c_2)) and c_i <= c_2
    skipped_by_h3 = np.isnan(c_i) or np.isnan(c_4)
    rows.append({"ts": str(ts), "close": None if np.isnan(c_i) else float(c_i), "close_m2_nan": bool(np.isnan(c_2)), "close_m4_nan": bool(np.isnan(c_4)),
                 "countdown_cond": bool(cond), "h3_skips_bar": bool(skipped_by_h3), "ind_cd": int(ind.loc[ts, "buy_cd"])})
bars_counted_by_ind_not_h3 = [r for r in rows if r["countdown_cond"] and r["h3_skips_bar"] and not np.isnan(s[pd.Timestamp(r["ts"])])]
say(f"  bars where close and close[-2] are valid and close<=close[-2] (a countdown bar by the definition) but harness3 skips them because close[-4] is NaN: {len(bars_counted_by_ind_not_h3)}")
for r in bars_counted_by_ind_not_h3:
    say(f"     {r['ts']} close {r['close']:.1f} close[-4] NaN -> independent cd={r['ind_cd']}")
# how often does that situation (valid close, valid close[-2], NaN close[-4]) occur in the whole hourly series?
c_all = s.to_numpy()
m = ~np.isnan(c_all[4:]) & ~np.isnan(c_all[2:-2]) & np.isnan(c_all[:-4])
say(f"  bars with valid close, valid close[-2], NaN close[-4] in the whole series: {int(m.sum())} (these are countdown-eligible by the definition but skipped by harness3 in NaN-in-place mode)")
OUT["buy13_nan_mode_mechanism"] = {"setup_start": str(start), "ind_13": str(t_ind), "h3_13": str(t_h3),
                                   "bars_skipped_by_h3_but_countdown_eligible": bars_counted_by_ind_not_h3, "n_such_bars_whole_series": int(m.sum())}

# (b) gap ground truth with tolerance split ------------------------------------------------------------------
say("\n==== (b) gap ground truth, matching tolerance 0 / 2 / 6 / 12 bars ====")
na = s.isna()
last_gap_end = s.index[na][-1]
tail = s[s.index > last_gap_end]
mask_src = na[(na.index >= "2024-11-17") & (na.index <= last_gap_end)].to_numpy()
L = min(len(tail), len(mask_src))
tail = tail.iloc[:L]; mask = mask_src[:L]
truth = H3.td_sequential(tail)
gapped = tail.copy(); gapped[mask] = np.nan
modes = {"skip": H3.td_sequential(gapped.dropna()).reindex(tail.index).fillna(0.0),
         "nan_reset": H3.td_sequential(gapped),
         "ffill": H3.td_sequential(gapped.ffill())}
res_b = {}
for mname, f in modes.items():
    res_b[mname] = {}
    for k in ("buy9", "sell9"):
        t = truth[k].astype(bool).to_numpy(); g = f[k].astype(bool).to_numpy()
        row = {"truth": int(t.sum()), "mode": int(g.sum())}
        for tol in (0, 2, 6, 12):
            w = 2 * tol + 1
            tw = pd.Series(t).rolling(w, center=True, min_periods=1).max().to_numpy().astype(bool)
            gw = pd.Series(g).rolling(w, center=True, min_periods=1).max().to_numpy().astype(bool)
            row[f"unmatched_tol{tol}"] = int((g & ~tw).sum()); row[f"missed_tol{tol}"] = int((t & ~gw).sum())
        res_b[mname][k] = row
        say(f"  {mname:9s} {k}: truth {row['truth']} got {row['mode']} | unmatched (no truth within +/-tol): " +
            ", ".join(f"tol{t_}={row[f'unmatched_tol{t_}']}" for t_ in (0, 2, 6, 12)) + " | missed: " +
            ", ".join(f"tol{t_}={row[f'missed_tol{t_}']}" for t_ in (0, 2, 6, 12)))
# rate per available bar
n_avail = int((~np.isnan(gapped.to_numpy())).sum())
say(f"  rate per 1000 bars: truth buy9 {truth['buy9'].sum()/L*1000:.2f} (L={L}); skip buy9 {modes['skip']['buy9'].sum()/n_avail*1000:.2f} per 1000 AVAILABLE bars (n_avail={n_avail}); skip per 1000 calendar hours {modes['skip']['buy9'].sum()/L*1000:.2f}")
res_b["rates"] = {"truth_buy9_per_1000": float(truth["buy9"].sum() / L * 1000), "skip_buy9_per_1000_available": float(modes["skip"]["buy9"].sum() / n_avail * 1000),
                  "truth_sell9_per_1000": float(truth["sell9"].sum() / L * 1000), "skip_sell9_per_1000_available": float(modes["skip"]["sell9"].sum() / n_avail * 1000), "L": L, "n_avail": n_avail}
# forward-return relevance: for skip-mode buy9 flags that do NOT coincide with a truth buy9 (tol 2), what is the
# 12-bar forward return on the complete series, vs matched ones and vs all bars?  (is the 'false' set different?)
t2 = pd.Series(truth["buy9"].astype(bool).to_numpy()).rolling(5, center=True, min_periods=1).max().to_numpy().astype(bool)
g = modes["skip"]["buy9"].astype(bool).to_numpy()
fwd12 = (tail.shift(-12) / tail - 1).to_numpy()
mdd = []
for lab, sel in (("skip matched", g & t2), ("skip unmatched", g & ~t2), ("truth all", truth["buy9"].astype(bool).to_numpy()), ("all bars", np.ones(L, bool))):
    v = fwd12[sel]; v = v[~np.isnan(v)]
    say(f"  fwd 12h return after {lab:14s}: mean {v.mean()*100:+.3f}% n={len(v)}")
    res_b[f"fwd12_{lab.replace(' ', '_')}"] = {"mean": float(v.mean()), "n": int(len(v))}
OUT["gap_ground_truth_tolerance"] = res_b

# (c) 4H frame as built by score3 ----------------------------------------------------------------------------
say("\n==== (c) 4H frame (resample('4h').last(), dropna), harness3 vs independent ====")
h4 = h.resample("4h").last()
OUT["h4"] = {}
for a in ("btc", "eth"):
    px = h4[a].dropna()
    f3 = H3.td_sequential(px); fi = td_ind(px)
    row = {}
    for k in FLAGS:
        d_ = int((f3[k].astype(bool) != fi[k].astype(bool)).sum())
        row[k] = {"n_h3": int(f3[k].sum()), "n_ind": int(fi[k].sum()), "n_diff_bars": d_}
    OUT["h4"][a] = row
    say(f"  {a}: " + ", ".join(f"{k} h3={row[k]['n_h3']} ind={row[k]['n_ind']} diff={row[k]['n_diff_bars']}" for k in FLAGS))
# eth 1H too
px = h["eth"].dropna(); f3 = H3.td_sequential(px); fi = td_ind(px)
OUT["h1_eth"] = {k: {"n_h3": int(f3[k].sum()), "n_ind": int(fi[k].sum()), "n_diff_bars": int((f3[k].astype(bool) != fi[k].astype(bool)).sum())} for k in FLAGS}
say("  eth 1H skip mode: " + ", ".join(f"{k} h3={OUT['h1_eth'][k]['n_h3']} ind={OUT['h1_eth'][k]['n_ind']} diff={OUT['h1_eth'][k]['n_diff_bars']}" for k in FLAGS))

# (d) where do the 1H flags fall relative to the gapped window ----------------------------------------------
say("\n==== (d) 1H BTC flags (skip mode) by period and by gapped window ====")
px = s.dropna(); f3 = H3.td_sequential(px).reindex(s.index).fillna(0.0)
gap_window = (s.index >= "2024-12-01") & (s.index <= "2025-03-31")
periods = {"train": (s.index >= "2024-11-01") & (s.index <= "2025-06-30"), "validation": (s.index >= "2025-07-01") & (s.index <= "2025-12-31"), "test": s.index >= "2026-01-01"}
OUT["h1_flags_by_period"] = {}
for k in FLAGS:
    fk = f3[k].astype(bool).to_numpy()
    row = {p: int((fk & m_).sum()) for p, m_ in periods.items()}
    row["train_in_gapped_dec24_mar25"] = int((fk & gap_window).sum())
    OUT["h1_flags_by_period"][k] = row
    say(f"  {k:7s} train {row['train']} (of which {row['train_in_gapped_dec24_mar25']} in Dec-2024..Mar-2025, the gapped window) | validation {row['validation']} | test {row['test']}")
say(f"  NaN share of hours inside Dec-2024..Mar-2025: {s[gap_window].isna().mean()*100:.1f}%; outside: {s[~gap_window].isna().mean()*100:.2f}%")
OUT["nan_share_gapped_window"] = float(s[gap_window].isna().mean())

with open(os.path.join(HERE, "td_compare_followup.json"), "w") as fh:
    json.dump(OUT, fh, indent=1, default=str)
say("\nwrote td_compare_followup.json")
