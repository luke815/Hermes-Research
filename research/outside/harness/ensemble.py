import numpy as np, pandas as pd, json, sys
import harness as H, harness2 as H2, harness3 as H3
d = pd.read_pickle("data/daily2.pkl")
px = d["btc"]
big = ["BNB","SOL","XRP","ADA","DOGE","LINK","AVAX","DOT"]
R = {"funding": d["btc_funding"], "oi_coins": d["oi_BTC"]/px, "basis": d["basis_btc"], "lsr": d["lsr_BTC"],
     "dvol": d["dvol_btc"], "skew": d["skew_btc"], "ivrv": d["atm_iv_btc"]/d["rv_btc"],
     "bigalt_funding": d[[f"funding_{a}" for a in big]].median(axis=1)}
FEAR = {"dvol","skew","ivrv"}
pct = {k: H.pct_rank(v, 365, 180) for k,v in R.items()}
chg = {k: H.pct_rank(v - v.shift(20), 365, 180) for k,v in R.items()}
trend = np.sign(px - px.rolling(200).mean()).where(px.rolling(200).mean().notna())
H3.td_columns(d, "btc")
buy = ((d["td_buy9_btc"]==1)|(d["td_buy13_btc"]==1)).rolling(5).max(); sell = ((d["td_sell9_btc"]==1)|(d["td_sell13_btc"]==1)).rolling(5).max()
td_vote = (buy.fillna(0) - sell.fillna(0)).clip(-1,1)
def level_vote(p, contrarian):
    v = pd.Series(np.nan, index=p.index); v[p>=0.8] = -1 if contrarian else 1; v[p<=0.2] = 1 if contrarian else -1; v[(p>0.2)&(p<0.8)] = 0; return v
def change_vote(p, up_positive=True):
    v = pd.Series(np.nan, index=p.index); v[p>=0.8] = 1 if up_positive else -1; v[p<=0.2] = -1 if up_positive else 1; v[(p>0.2)&(p<0.8)] = 0; return v
def score(votes):
    V = pd.concat(votes, axis=1); return V.mean(axis=1).where(V.notna().sum(axis=1) >= 4)
V1 = score([level_vote(pct[k], k not in FEAR) for k in R] + [trend, td_vote])
V2 = score([change_vote(chg[k], True) for k in R] + [trend, td_vote])
V3 = score([change_vote(chg[k], k not in FEAR) for k in R] + [trend, td_vote])
heat = d["heat"]
scores = {"V1 textbook levels": V1, "V2 turning up": V2, "V3 turning up signed": V3, "heat (Hermes)": heat}
def evaluate(s, name, quiet=False):
    s = s.shift(1)
    out = {}
    lines = [f"== {name}: share positive {float((s>=0.4).mean()):.2f}, negative {float((s<=-0.4).mean()):.2f} (of all days)"]
    for h in (10, 30, 60):
        fwd = px.shift(-h)/px - 1
        row = {}
        for pname in H.PERIODS:
            m = H2.slice_period(s, pname, "1d"); y = H2.slice_period(fwd, pname, "1d")
            ok = m.notna() & y.notna(); m = m[ok]; y = y[ok]
            pos = m >= 0.4; neg = m <= -0.4
            if pos.sum() < 3 or neg.sum() < 3: row[pname] = None; continue
            spread = float(y[pos].mean() - y[neg].mean())
            t, _ = H.nw_t(y.to_numpy(float), (pos.astype(float) - neg.astype(float)).to_numpy(float), h)
            row[pname] = {"pos_mean": float(y[pos].mean()), "neg_mean": float(y[neg].mean()), "all": float(y.mean()), "spread": spread, "t": t,
                          "hit_pos": float((y[pos] > 0).mean()), "hit_neg": float((y[neg] > 0).mean()),
                          "n_pos": H2.clusters(y[pos].index, h, "1d"), "n_neg": H2.clusters(y[neg].index, h, "1d")}
        out[h] = row
        lines.append(f"h={h}: " + " | ".join(f"{p[:3]} " + (f"pos {r['pos_mean']*100:+.1f}% neg {r['neg_mean']*100:+.1f}% all {r['all']*100:+.1f}% spread {r['spread']*100:+.1f}% t={r['t']:.1f} n={r['n_pos']}/{r['n_neg']} hit {r['hit_pos']:.2f}/{r['hit_neg']:.2f}" if r else "-") for p, r in row.items()))
    mdd = H2.forward_mdd(px, 30)
    for pname in H.PERIODS:
        m = H2.slice_period(s, pname, "1d"); dd = H2.slice_period(mdd, pname, "1d"); ok = m.notna() & dd.notna(); m = m[ok]; dd = dd[ok]
        neg = m <= -0.4
        if neg.sum() >= 3:
            lines.append(f"   risk {pname[:3]}: P(10% drop in 30d | negative) {float((dd[neg]<=-0.1).mean()):.2f} vs all {float((dd<=-0.1).mean()):.2f}; mdd30 {dd[neg].mean()*100:+.1f}% vs {dd.mean()*100:+.1f}%")
    # calibration by decile, 30d
    fwd = px.shift(-30)/px - 1
    for pname in ("train", "validation", "test"):
        m = H2.slice_period(s, pname, "1d"); y = H2.slice_period(fwd, pname, "1d"); ok = m.notna() & y.notna(); m = m[ok]; y = y[ok]
        if len(m) < 100: continue
        dec = pd.qcut(m.rank(method="first"), 10, labels=False)
        means = y.groupby(dec).mean()
        rk = pd.Series(means.values).rank(); rho = float(np.corrcoef(rk, np.arange(10))[0, 1])  # Spearman without scipy
        lines.append(f"   calibration {pname[:3]}: 30d mean by score decile " + " ".join(f"{v*100:+.0f}" for v in means.values) + f" | spearman {rho:+.2f}")
    if not quiet: print("\n".join(lines))
    return out
results = {name: evaluate(s, name) for name, s in scores.items()}
# placebo: random sign flips of V1 components
rng = np.random.default_rng(7); keys = list(R)
pl = []
for i in range(200):
    flips = {k: rng.choice([-1, 1]) for k in keys}
    s = score([level_vote(pct[k], k not in FEAR) * flips[k] for k in keys] + [trend * rng.choice([-1, 1]), td_vote * rng.choice([-1, 1])]).shift(1)
    fwd = px.shift(-30)/px - 1; vals = []
    for pname in ("train", "validation"):
        m = H2.slice_period(s, pname, "1d"); y = H2.slice_period(fwd, pname, "1d"); ok = m.notna() & y.notna(); m = m[ok]; y = y[ok]
        pos = m >= 0.4; neg = m <= -0.4
        if pos.sum() < 3 or neg.sum() < 3: vals.append(None); continue
        t, _ = H.nw_t(y.to_numpy(float), (pos.astype(float) - neg.astype(float)).to_numpy(float), 30); vals.append(t)
    pl.append(vals)
pl = [v for v in pl if None not in v]
tv = [abs(v[1]) for v in pl]; same = [np.sign(v[0]) == np.sign(v[1]) and abs(v[1]) >= 2.5 for v in pl]
print(f"\nplacebo (random vote signs, {len(pl)} draws): validation |t| >= 2.5 in {np.mean([x>=2.5 for x in tv]):.2f} of draws; same-sign train/val AND val |t|>=2.5 in {np.mean(same):.2f}")
json.dump({k: {str(h): v for h, v in r.items()} for k, r in results.items()}, open("results3/ensemble_results.json", "w"), indent=1, default=float)
