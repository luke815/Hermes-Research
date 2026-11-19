"""Units, data-break and episode-date diagnostics (no scoring)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, RES)
import numpy as np, pandas as pd
import harness as H, harness2 as H2, harness3 as H3
df = pd.read_pickle(os.path.join(RES, "data", "daily2.pkl"))
print("== funding units ==")
m = df[["perp_funding_btc", "btc_funding"]].dropna()
print(m.describe().T[["50%", "mean", "min", "max"]])
print("ratio btc_funding/perp_funding_btc median:", (m["btc_funding"] / m["perp_funding_btc"]).median())
print("perp_funding_btc == 0.0001 share:", (df["perp_funding_btc"] == 0.0001).mean(), " == 0.01 share:", (df["perp_funding_btc"] == 0.01).mean())
print("\n== liq_BTC and oi_BTC by year (median) ==")
y = df[["liq_BTC", "oi_BTC", "liq_ETH", "oi_ETH", "lsr_BTC"]].groupby(df.index.year).median()
y["liq/oi_BTC"] = y["liq_BTC"] / y["oi_BTC"]
print(y.to_string())
print("\n== td_buy9_eth completions in validation and test (the single R4 PASS cell), with forward 10d mdd ==")
td = H3.td_columns(df.copy(), "eth")
flag = td["td_buy9_eth"].shift(1).fillna(0).astype(bool)
mdd10 = H2.forward_mdd(df["eth"], 10); r10 = df["eth"].shift(-10) / df["eth"] - 1
for p in ["validation", "test"]:
    f = H2.slice_period(flag, p, "1d"); idx = f[f].index
    print(p, "flagged dates:", [str(d.date()) for d in idx])
    print("   mdd10 on those bars:", [f"{mdd10[d]*100:+.1f}%" for d in idx], " r10:", [f"{r10[d]*100:+.1f}%" for d in idx],
          " vs period mean mdd10:", f"{H2.slice_period(mdd10,p,'1d').mean()*100:+.1f}%")
print("\n== lsr_BTC pct365>=0.8 episode start dates (h=30 clusters), lag=1 ==")
lsr_top = (H.pct_rank(df["lsr_BTC"], 365, 180) >= 0.8).shift(1).fillna(False).astype(bool)
r14 = df["btc"].pct_change(14)
for p in H.PERIODS:
    f = H2.slice_period(lsr_top, p, "1d"); idx = f[f].index
    starts = [idx[0]] + [idx[i] for i in range(1, len(idx)) if (idx[i] - idx[i-1]).days > 30] if len(idx) else []
    print(p, f"n_bars={len(idx)} episodes(30)={len(starts)}:", [f"{d.date()} (14d ret before {r14[d]*100:+.0f}%)" for d in starts])
print("\n== perp_oi_btc USD pct365>=0.8 episode start dates (h=30), lag=1 ==")
oi_top = (H.pct_rank(df["perp_oi_btc"], 365, 180) >= 0.8).shift(1).fillna(False).astype(bool)
for p in H.PERIODS:
    f = H2.slice_period(oi_top, p, "1d"); idx = f[f].index
    starts = [idx[0]] + [idx[i] for i in range(1, len(idx)) if (idx[i] - idx[i-1]).days > 30] if len(idx) else []
    print(p, f"n_bars={len(idx)} episodes(30)={len(starts)}:", [str(d.date()) for d in starts])
print("\n== perp_funding_btc pct365>=0.8 episode start dates (h=20), lag=1 ==")
fund_top = (H.pct_rank(df["perp_funding_btc"], 365, 180) >= 0.8).shift(1).fillna(False).astype(bool)
for p in H.PERIODS:
    f = H2.slice_period(fund_top, p, "1d"); idx = f[f].index
    starts = [idx[0]] + [idx[i] for i in range(1, len(idx)) if (idx[i] - idx[i-1]).days > 20] if len(idx) else []
    print(p, f"n_bars={len(idx)} episodes(20)={len(starts)}:", [str(d.date()) for d in starts])
