"""Episode counts for divergence flags and trailing-90 event targets (counts only, no scoring)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, RES)
import numpy as np, pandas as pd
import harness as H, harness2 as H2
df = pd.read_pickle(os.path.join(RES, "data", "daily2.pkl"))
PER = list(H.PERIODS)
def per(s, p): return H2.slice_period(s, p, "1d")
def pct(s, w=365, mp=180): return H.pct_rank(s, w, mp)
def eps(flag, hs, label):
    f = flag.shift(1).fillna(False).astype(bool); parts = []
    for p in PER:
        fp = per(f, p); idx = fp[fp].index
        parts.append(f"{p[:3]} bars={int(fp.sum()):4d} " + " ".join(f"ep{h}={H2.clusters(idx, h, '1d')}" for h in hs))
    tv = f[(f.index <= "2025-12-31")]; idx = tv[tv].index
    parts.append("tr+va " + " ".join(f"ep{h}={H2.clusters(idx, h, '1d')}" for h in hs))
    print(f"  {label:62s} | " + " | ".join(parts))
btc = df["btc"]; fp = pct(df["perp_funding_btc"]); bp = pct(df["basis_btc"])
coin_oi = df["futures_oi_btc"] / btc; d7 = pct(coin_oi.pct_change(7))
print("==== A3 candidates: divergences ====")
eps((fp >= 0.8) & (d7 <= 0.2), (10, 20), "funding top AND coin futures_oi 7d chg pct<=0.2 (paying up, OI leaving)")
eps((fp >= 0.8) & (d7 >= 0.8), (10, 20), "funding top AND coin futures_oi 7d chg pct>=0.8 (paying up, OI building)")
eps((fp >= 0.8) & (bp <= 0.4), (10, 20, 30), "funding top AND basis pct<=0.4 (perp crowded, term not)")
eps((bp >= 0.8) & (fp <= 0.4), (10, 20, 30), "basis top AND funding pct<=0.4 (term rich, perp not)")
eps((bp >= 0.8) & (fp >= 0.8), (10, 20, 30), "reference: basis top AND funding top (tested in PREREG2 risk)")
eps(((fp - bp) >= 0.5), (10, 20, 30), "funding pct minus basis pct >= 0.5")
eps(((bp - fp) >= 0.5), (10, 20, 30), "basis pct minus funding pct >= 0.5")
print("\n==== A1 event targets on trailing-90-day percentiles (saturation check) ====")
liq_n = df["liq_BTC"] / df["oi_BTC"]
events = {
 "liq norm pct90>=0.9": pct(liq_n, 90, 60) >= 0.9,
 "liq raw log-chg z90>=2 (vs 90d mean)": H.zscore(np.log(df["liq_BTC"].replace(0, np.nan)), 90, 60) >= 2,
 "OI flush coin 3d chg pct90<=0.1": pct(coin_oi.pct_change(3), 90, 60) <= 0.1,
 "OI flush coin 3d chg <= -5%": coin_oi.pct_change(3) <= -0.05,
 "DVOL 5d chg pct90>=0.9": pct(df["dvol_lv_btc"].diff(5), 90, 60) >= 0.9,
 "funding reset: pct365<0.5 today, >=0.8 in last 5d": (fp < 0.5) & (fp.shift(1).rolling(5).max() >= 0.8),
}
for k, ev in events.items():
    ev = ev.fillna(False).astype(bool)
    w = {N: ev[::-1].rolling(N, min_periods=1).max()[::-1].shift(-1).where(ev.shift(-N).notna()) for N in (10, 20)}
    row = []
    for p in PER:
        e = per(ev, p); row.append(f"{p[:3]} days={int(e.sum()):3d} ep10={H2.clusters(e[e].index, 10, '1d'):2d} P(w10)={per(w[10], p).mean():.2f} P(w20)={per(w[20], p).mean():.2f}")
    print(f"  {k:50s} | " + " | ".join(row))
print("\n==== A2 robustness: quadrants with futures_oi coin, BTC ====")
dpx = btc.pct_change(7)
eps((dpx > 0) & (d7 >= 0.8), (10, 20), "leveraged rally (futures_oi coin)")
eps((dpx < 0) & (d7 <= 0.2), (10, 20), "long flush (futures_oi coin)")
eps((dpx > 0) & (d7 >= 0.8) & (fp >= 0.8), (10, 20), "leveraged rally AND funding top (the overheated subset)")
