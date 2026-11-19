"""Completeness critic, 2026-11-19. COUNTS ONLY: flagged bars, independent episodes (harness2.clusters, lag=1),
state transition matrices (base rates), unconditional crash base rates, and two overlap diagnostics.
Nothing here is a score: no forward-return or drawdown difference is computed for any new flag."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, RES)
import numpy as np, pandas as pd
import harness as H, harness2 as H2
pd.set_option("display.width", 220)
df = pd.read_pickle(os.path.join(RES, "data", "daily2.pkl"))
PER = list(H.PERIODS)
def per(s, p): return H2.slice_period(s, p, "1d")
def pct(s): return H.pct_rank(s, 365, 180)
def eps(flag, hs, label):
    f = flag.shift(1).fillna(False).astype(bool)  # lag=1 entry
    parts = []
    for p in PER:
        fp = per(f, p); idx = fp[fp].index
        parts.append(f"{p[:3]} bars={int(fp.sum()):4d} " + " ".join(f"ep{h}={H2.clusters(idx, h, '1d')}" for h in hs))
    tv = f[(f.index <= "2025-12-31")]; idx = tv[tv].index
    parts.append("tr+va " + " ".join(f"ep{h}={H2.clusters(idx, h, '1d')}" for h in hs))
    print(f"  {label:58s} | " + " | ".join(parts))

btc, eth = df["btc"], df["eth"]
fp_b, fp_e = pct(df["perp_funding_btc"]), pct(df["perp_funding_eth"])
oi_usd_b = df["perp_oi_btc"]; oi_coin_b = df["perp_oi_btc"] / btc
foi_usd_b = df["futures_oi_btc"]; foi_coin_b = df["futures_oi_btc"] / btc
oi_usd_e = df["perp_oi_eth"]; oi_coin_e = df["perp_oi_eth"] / eth

print("\n==== A1. Crowding -> observable events: event-day base rates (unconditional) and crowded-state episodes ====")
crowd_b = fp_b >= 0.8
crowd_pair = crowd_b & (pct(foi_usd_b) >= 0.8)
eps(crowd_b, (10, 20), "flag: perp_funding_btc pct365>=0.8")
eps(fp_b >= 0.9, (10, 20), "flag: perp_funding_btc pct365>=0.9")
eps(crowd_pair, (10, 20), "flag: funding top AND futures_oi top (0.8)")
eps(fp_e >= 0.8, (10, 20), "flag: perp_funding_eth pct365>=0.8")
liq_norm = df["liq_BTC"] / df["oi_BTC"]
events = {
 "liq cascade raw: liq_BTC pct365>=0.9": pct(df["liq_BTC"]) >= 0.9,
 "liq cascade norm: (liq_BTC/oi_BTC) pct365>=0.9": pct(liq_norm) >= 0.9,
 "OI flush USD: futures_oi_btc 3d%chg pct365<=0.1": pct(foi_usd_b.pct_change(3)) <= 0.1,
 "OI flush coin: (futures_oi_btc/btc) 3d%chg pct365<=0.1": pct(foi_coin_b.pct_change(3)) <= 0.1,
 "OI flush USD -5%/3d absolute": foi_usd_b.pct_change(3) <= -0.05,
 "funding reset: pct<0.5 today, >=0.8 within last 5d": (fp_b < 0.5) & (fp_b.shift(1).rolling(5).max() >= 0.8),
 "DVOL spike: dvol_lv_btc 5d chg pct365>=0.9": pct(df["dvol_lv_btc"].diff(5)) >= 0.9,
 "dispersion spike: dispersion_14 pct365>=0.9": pct(df["dispersion_14"]) >= 0.9,
}
for k, ev in events.items():
    ev = ev.fillna(False).astype(bool)
    within = {N: ev[::-1].rolling(N, min_periods=1).max()[::-1].shift(-1).where(ev.shift(-N).notna()) for N in (10, 20)}
    row = []
    for p in PER:
        e = per(ev, p); row.append(f"{p[:3]} days={int(e.sum()):3d} ep10={H2.clusters(e[e].index, 10, '1d'):2d} P(within10)={per(within[10], p).mean():.2f} P(within20)={per(within[20], p).mean():.2f}")
    print(f"  event {k:52s} | " + " | ".join(row))

print("\n==== A2. Price x coin-OI quadrants (7-day), BTC; flags at the quintile of the 7d OI change ====")
dpx = btc.pct_change(7); doi_c = pct(oi_coin_b.pct_change(7)); doi_u = pct(oi_usd_b.pct_change(7))
eps((dpx > 0) & (doi_c >= 0.8), (10, 20), "leveraged rally: px7d>0 AND coinOI 7d chg pct>=0.8")
eps((dpx < 0) & (doi_c <= 0.2), (10, 20), "long flush: px7d<0 AND coinOI 7d chg pct<=0.2")
eps((dpx > 0) & (doi_c <= 0.2), (10, 20), "short covering: px7d>0 AND coinOI 7d chg pct<=0.2")
eps((dpx < 0) & (doi_c >= 0.8), (10, 20), "new shorts: px7d<0 AND coinOI 7d chg pct>=0.8")
eps((dpx > 0) & (doi_u >= 0.8), (10, 20), "control: same with USD OI (leveraged rally)")
dpx_e = eth.pct_change(7); doi_ce = pct(oi_coin_e.pct_change(7))
eps((dpx_e > 0) & (doi_ce >= 0.8), (10, 20), "ETH leveraged rally (coin OI)")
eps((dpx_e < 0) & (doi_ce <= 0.2), (10, 20), "ETH long flush (coin OI)")

print("\n==== A3. Coin-OI high vs USD-OI high vs price high (overlap diagnostic, not a score) ====")
px_top = pct(btc) >= 0.8
for name, s in [("perp_oi USD", oi_usd_b), ("perp_oi coin", oi_coin_b), ("futures_oi USD", foi_usd_b), ("futures_oi coin", foi_coin_b)]:
    top = pct(s) >= 0.8
    eps(top, (30, 60), f"flag: {name} pct365>=0.8")
    row = []
    for p in PER:
        t, x = per(top, p), per(px_top, p); m = t.notna() & x.notna()
        if t[m].sum() >= 3:
            row.append(f"{p[:3]} P(price top|OI top)={x[m][t[m]].mean():.2f} vs P(price top)={x[m].mean():.2f} corr(pct)={per(pct(s), p).corr(per(pct(btc), p)):.2f}")
    print(f"     overlap {name:16s} | " + " | ".join(row))
eps(px_top, (30, 60), "control: btc price pct365>=0.8")
eps(pct(oi_coin_b) >= 0.8, (30, 60), "coin OI top (pct365>=0.8), dup for ep30")
eps((pct(oi_coin_b) >= 0.8) & ~px_top, (30, 60), "coin OI top AND price NOT top (the clean cell)")
eps((pct(oi_coin_e) >= 0.8), (30, 60), "ETH perp_oi coin pct365>=0.8")

print("\n==== A4. Breadth of alt crowding (share of 18 alts with funding pct365>=0.8) ====")
alts = H.ALTS
fpcts = pd.DataFrame({a: pct(df[f"funding_{a}"]) for a in alts})
navail = fpcts.notna().sum(axis=1)
breadth = (fpcts >= 0.8).sum(axis=1) / navail.replace(0, np.nan)
breadth = breadth.where(navail >= 10)
for p in PER:
    b = per(breadth, p).dropna()
    print(f"  {p[:3]} breadth: n={len(b)} mean={b.mean():.2f} q50={b.quantile(.5):.2f} q80={b.quantile(.8):.2f} q90={b.quantile(.9):.2f} share(>=0.5)={(b>=0.5).mean():.2f}")
eps(breadth >= 0.5, (10, 20, 30), "flag: breadth >= 0.5 (absolute)")
eps(pct(breadth) >= 0.8, (10, 20, 30), "flag: breadth pct365 >= 0.8 (relative)")
eps((breadth >= 0.5) & (fp_b < 0.8), (10, 20, 30), "flag: breadth>=0.5 AND BTC funding NOT crowded")
eps(breadth <= 0.05, (10, 20, 30), "mirror: breadth <= 0.05 (no alt crowded)")
# dashboard funding default-tie diagnostic
for a in ["SOL", "DOGE", "XRP"]:
    s = df[f"funding_{a}"].dropna(); print(f"     funding_{a}: share exactly 0.01 = {(s==0.01).mean():.2f}, share==0 = {(s==0).mean():.2f}")
s = df["btc_funding"].dropna(); print(f"     btc_funding (=perp_funding*100 in daily2): share exactly 0.01 = {(s==0.01).mean():.2f}")

print("\n==== A5. Funding-state transition matrices (BASE RATES), state from perp_funding pct365: C>=0.8, W<=0.2, N otherwise ====")
def states(fpct):
    s = pd.Series(np.where(fpct >= 0.8, "C", np.where(fpct <= 0.2, "W", "N")), index=fpct.index, dtype=object)
    return s.where(fpct.notna())
for asset, fpc in [("BTC", fp_b), ("ETH", fp_e)]:
    S = states(fpc)
    for p in PER + ["2025 only", "2026 vs 2024H2-2025"]:
        if p in PER: Sp = per(S, p)
        elif p == "2025 only": Sp = S["2025-01-01":"2025-12-31"]
        else: continue
        Sp = Sp.dropna()
        occ = Sp.value_counts(normalize=True).reindex(["C", "N", "W"]).fillna(0)
        runs = (Sp != Sp.shift()).cumsum(); rl = Sp.groupby(runs).agg(["first", "size"])
        mrl = rl.groupby("first")["size"].agg(["mean", "median", "max", "count"]).reindex(["C", "N", "W"])
        print(f"  {asset} {p:10s} n={len(Sp)} occupancy C={occ['C']:.2f} N={occ['N']:.2f} W={occ['W']:.2f} | run length (days) mean/median/max/#runs: " +
              " ".join(f"{st}={mrl.loc[st,'mean']:.0f}/{mrl.loc[st,'median']:.0f}/{mrl.loc[st,'max']:.0f}/{int(mrl.loc[st,'count'])}" if not np.isnan(mrl.loc[st, 'mean']) else f"{st}=-" for st in ["C", "N", "W"]))
        for k in (7, 14, 30):
            fut = S.shift(-k).reindex(Sp.index)
            m = fut.notna(); T = pd.crosstab(Sp[m], fut[m], normalize="index").reindex(index=["C", "N", "W"], columns=["C", "N", "W"]).fillna(0)
            cnt = pd.crosstab(Sp[m], fut[m]).reindex(index=["C", "N", "W"], columns=["C", "N", "W"]).fillna(0).sum(axis=1)
            epc = {st: H2.clusters(Sp[m][Sp[m] == st].index, k, "1d") for st in ["C", "N", "W"]}
            print(f"       k={k:2d}: " + " | ".join(f"from {st} (days={int(cnt[st]):4d}, ep={epc[st]:3d}) -> C {T.loc[st,'C']:.2f} N {T.loc[st,'N']:.2f} W {T.loc[st,'W']:.2f}" for st in ["C", "N", "W"]))

print("\n==== A6. Funding cooling inside/after the crowded state, conditioned on price (BTC) ====")
r5 = btc.pct_change(5)
cool = (fp_b.shift(5) >= 0.8) & (fp_b < 0.6)
eps(cool, (10, 20, 30), "cooling: pct>=0.8 at t-5 AND pct<0.6 at t")
eps(cool & (r5 > -0.03), (10, 20, 30), "healthy reset: cooling AND 5d return > -3%")
eps(cool & (r5 <= -0.03), (10, 20, 30), "flush reset: cooling AND 5d return <= -3%")
eps(crowd_b & (df["perp_funding_btc"].diff(3) > 0), (10, 20), "crowded AND funding rising (3d diff>0)")
eps(crowd_b & (df["perp_funding_btc"].diff(3) < 0), (10, 20), "crowded AND funding falling (3d diff<0)")
eps((r5 > -0.03) & (fp_b < 0.6), (10, 20, 30), "control: 5d return > -3% AND pct<0.6 (no prior crowding)")

print("\n==== Base rates for the dashboard: unconditional forward-drawdown frequencies ====")
for asset, px in [("BTC", btc), ("ETH", eth)]:
    for W, thr in [(10, -0.10), (20, -0.10), (30, -0.10), (60, -0.20), (90, -0.20)]:
        d = H2.forward_mdd(px, W); row = []
        for p in PER:
            dp = per(d, p).dropna(); row.append(f"{p[:3]} P(mdd{W}<={int(thr*100)}%)={(dp<=thr).mean():.2f} mean mdd={dp.mean()*100:+.1f}% (n={len(dp)})")
        print(f"  {asset} W={W:2d}: " + " | ".join(row))

print("\n==== Diagnostic for the lsr result: does lsr_BTC top coincide with recent weakness? (overlap, not a score) ====")
lsr_top = pct(df["lsr_BTC"]) >= 0.8; r14 = btc.pct_change(14)
for p in PER:
    t, r = per(lsr_top, p), per(r14, p); m = t.notna() & r.notna()
    print(f"  {p[:3]} P(14d ret<0 | lsr top)={(r[m][t[m]]<0).mean():.2f} vs P(14d ret<0)={(r[m]<0).mean():.2f}; mean 14d ret | lsr top = {r[m][t[m]].mean()*100:+.1f}% vs all {r[m].mean()*100:+.1f}%; corr(lsr pct, 14d ret)={per(pct(df['lsr_BTC']),p).corr(r):.2f}")
eps(lsr_top, (10, 20, 30), "lsr_BTC pct365>=0.8 (for reference)")
eps(lsr_top & (r14 >= 0), (10, 20, 30), "lsr top AND 14d return >= 0 (the clean cell)")

print("\n==== 2026 regime descriptives ====")
for p in PER:
    print(f"  {p[:3]}: median perp_funding_btc per 8h = {per(df['perp_funding_btc'], p).median()*1e4:.2f} bp; share days pct>=0.8 = {(per(fp_b,p)>=0.8).mean():.2f}; share pct<=0.2 = {(per(fp_b,p)<=0.2).mean():.2f}; "
          f"coin OI (perp) median = {per(oi_coin_b,p).median():,.0f} BTC; median dvol_lv_btc = {per(df['dvol_lv_btc'],p).median():.1f}; mean |btc 1d ret| = {per(btc.pct_change(),p).abs().mean()*100:.2f}%")
print(f"  test period length: {len(per(btc, 'test'))} days ({per(btc,'test').index.min().date()} .. {per(btc,'test').index.max().date()})")
