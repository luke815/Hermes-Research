"""Follow-up numbers for the OI refutation: baseline means, drop-one-episode sensitivity, price-top-without-OI cells."""
import os, sys, json
import numpy as np, pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
import harness as H, harness2 as H2
df = pd.read_pickle(os.path.join(ROOT, "data", "daily2.pkl"))
for a in ("btc", "eth"):
    df[f"price_{a}"] = df[a]
out = {}
print("A. Train-period mean forward return: full train (2019-01..2024-06) vs signal-available (perp_oi pct365 notna, 2021-09..2024-06)")
for a in ("btc", "eth"):
    px = H.price(df, a)
    _, sig = H2.make_flag(df, (f"perp_oi_{a}", "pct365", "top", 0.8), "1d", 1)
    avail = sig.notna()
    for h in (30, 60, 90):
        fwd = (px.shift(-h) / px - 1)
        tr = H2.slice_period(fwd, "train", "1d").dropna()
        av = tr[H2.slice_period(avail, "train", "1d").reindex(tr.index).fillna(False)]
        pre = tr[~H2.slice_period(avail, "train", "1d").reindex(tr.index).fillna(False)]
        out[f"{a}:h{h}"] = {"mean_full_train": float(tr.mean()), "mean_avail": float(av.mean()), "mean_pre_avail_2019_2021": float(pre.mean()),
                            "first_avail": str(av.index.min().date()), "n_avail": int(len(av)), "n_pre": int(len(pre))}
        print(f"  {a} h={h}: full-train mean {tr.mean()*100:+.1f}% | signal-available mean {av.mean()*100:+.1f}% (from {av.index.min().date()}, n={len(av)}) | 2019..pre-signal mean {pre.mean()*100:+.1f}% (n={len(pre)})")

print("\nB. ETH validation drop-one-episode sensitivity, USD perp_oi top 0.8, h=60 and h=90 (episodes gap>h)")
def eps(index, h):
    d = np.array(sorted(index)); groups=[[d[0]]]
    for p_, n_ in zip(d[:-1], d[1:]):
        if (n_-p_)/np.timedelta64(1,"D") > h: groups.append([n_])
        else: groups[-1].append(n_)
    return groups
for a in ("eth", "btc"):
    px = H.price(df, a)
    for src in ("perp_oi",):
        f, _ = H2.make_flag(df, (f"{src}_{a}", "pct365", "top", 0.8), "1d", 1)
        for h in (60, 90):
            fwd = px.shift(-h)/px-1
            y = H2.slice_period(fwd, "validation", "1d"); ff = H2.slice_period(f, "validation", "1d")
            m = y.notna(); y, ff = y[m], ff[m].fillna(False).astype(bool)
            base = y.mean(); flagged = y[ff]
            print(f"  {a} {src} h={h} validation: excess all {flagged.mean()-base:+.3f} (n_flag={len(flagged)})")
            for g in eps(flagged.index, h):
                idx = pd.DatetimeIndex(g); rest = flagged.drop(idx)
                print(f"     drop {idx[0].date()}..{idx[-1].date()} ({len(idx)} bars, own excess {flagged.loc[idx].mean()-base:+.3f}) -> remaining excess {rest.mean()-base if len(rest) else float('nan'):+.3f} over {len(rest)} bars")

print("\nC. PRICE top 0.8 & USD perp_oi NOT top (pct<0.8), and & USD futures_oi NOT top: is price-at-high alone negative in validation?")
for a in ("btc", "eth"):
    px = H.price(df, a)
    fp, sp = H2.make_flag(df, (f"price_{a}", "pct365", "top", 0.8), "1d", 1)
    for src in ("perp_oi", "futures_oi"):
        fu, su = H2.make_flag(df, (f"{src}_{a}", "pct365", "top", 0.8), "1d", 1)
        flag = fp & (su < 0.8) & su.notna()
        flag2 = fp & fu
        for h in (30, 60, 90):
            fwd = px.shift(-h)/px-1
            parts = []
            for lab, fl in (("price&!OI", flag), ("price&OI", flag2)):
                sub = []
                for p in ("train", "validation", "test"):
                    y = H2.slice_period(fwd, p, "1d"); ff = H2.slice_period(fl, p, "1d")
                    m = y.notna(); y, ff = y[m], ff[m].fillna(False).astype(bool)
                    if ff.sum() < 3: sub.append(f"{p[:3]} -"); continue
                    ex = y[ff].mean()-y.mean(); t,_ = H.nw_t(y.to_numpy(float), ff.to_numpy(float), h)
                    sub.append(f"{p[:3]} {ex*100:+.1f}% t={t:+.1f} n_ind={H2.clusters(y[ff].index,h,'1d')} n={int(ff.sum())}")
                parts.append(f"[{lab}] " + " | ".join(sub))
            print(f"  {a} {src} h={h}: " + "  ||  ".join(parts))

print("\nD. Validation ETH: what fraction of USD perp_oi top bars fall in Jul-2024 / Nov-2024..Feb-2025 / May-Oct 2025?")
a="eth"; f,_ = H2.make_flag(df, ("perp_oi_eth","pct365","top",0.8),"1d",1)
v = H2.slice_period(f, "validation", "1d"); v = v[v]
print("  ", v.groupby(v.index.to_period("M")).size().to_dict())
json.dump(out, open(os.path.join(ROOT, "results3", "refute", "refute_oi_followup.json"), "w"), indent=1)
