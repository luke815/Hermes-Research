"""PREREG5: flows and macro readings scored with the pass-2 harness on BTC. Writes results3/macro_report.txt."""
import json, os, sys, time
import numpy as np, pandas as pd
import harness as H, harness2 as H2

HERE = os.path.dirname(os.path.abspath(__file__))
M = os.path.join(HERE, "data", "macro")
d = pd.read_pickle(os.path.join(HERE, "data", "daily2.pkl"))
idx = d.index


def fred(name):
    f = pd.read_csv(os.path.join(M, name + ".csv"))
    f.columns = ["date", "v"]
    f["v"] = pd.to_numeric(f["v"], errors="coerce")
    s = pd.Series(f["v"].values, index=pd.to_datetime(f["date"])).dropna()
    return s.reindex(idx.union(s.index)).ffill().reindex(idx)  # forward-fill onto the crypto calendar


def llama(name):
    j = json.load(open(os.path.join(M, name + ".json")))
    s = pd.Series({pd.Timestamp(time.strftime("%Y-%m-%d", time.gmtime(int(r["date"])))): r["totalCirculating"]["peggedUSD"] for r in j})
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s.reindex(idx)


stable = (llama("usdt") + llama("usdc"))
d["stable_supply"] = stable
d["stable_chg30"] = stable.pct_change(30) * 100
d["dxy_chg20"] = fred("DTWEXBGS").pct_change(20) * 100
d["real10_chg20"] = fred("DFII10").diff(20)
d["fed_chg4w"] = fred("WALCL").pct_change(28) * 100
d["spx_ret20"] = fred("SP500").pct_change(20) * 100
d["ndx_ret20"] = fred("NASDAQCOM").pct_change(20) * 100
d["vix"] = fred("VIXCLS")
d["vix_chg5"] = fred("VIXCLS").diff(5)
d["us10y_chg20"] = fred("DGS10").diff(20)
cbp = os.path.join(M, "cb_premium.csv")
if os.path.exists(cbp):
    c = pd.read_csv(cbp, parse_dates=["date"]).set_index("date")["premium"].reindex(idx)
    d["cb_premium"] = c * 100
    d["cb_premium_5d"] = (c * 100).rolling(5).mean()
etf = os.path.join(M, "etf_flows.csv")
if os.path.exists(etf):
    e = pd.read_csv(etf, parse_dates=["date"]).set_index("date")["flow"].reindex(idx).fillna(0)
    d["etf_flow10"] = e.rolling(10).sum()

CELLS = [  # (series, side, hypothesis sign for BTC)
    ("stable_chg30", "top", +1), ("stable_chg30", "bottom", -1),
    ("dxy_chg20", "top", -1), ("dxy_chg20", "bottom", +1),
    ("real10_chg20", "top", -1), ("real10_chg20", "bottom", +1),
    ("fed_chg4w", "top", +1), ("fed_chg4w", "bottom", -1),
    ("spx_ret20", "top", +1), ("spx_ret20", "bottom", -1),
    ("ndx_ret20", "top", +1), ("ndx_ret20", "bottom", -1),
    ("vix", "top", +1), ("vix", "bottom", -1), ("vix_chg5", "top", -1),
    ("us10y_chg20", "top", -1), ("us10y_chg20", "bottom", +1),
    ("cb_premium_5d", "top", +1), ("cb_premium_5d", "bottom", -1),
    ("etf_flow10", "top", +1), ("etf_flow10", "bottom", -1),
]
lines = []
say = lambda *a: (print(*a), lines.append(" ".join(str(x) for x in a)))
say("series coverage:")
for s in sorted({c[0] for c in CELLS}):
    if s in d:
        v = d[s].dropna(); say(f"  {s:16s} {v.index[0].date()}..{v.index[-1].date()} n={len(v)} last={v.iloc[-1]:.3g}")
    else:
        say(f"  {s:16s} not available")
passes = []
summary = []
for series, side, hyp in CELLS:
    if series not in d:
        continue
    thr = 0.8 if side == "top" else 0.2
    spec = (series, "pct365", side, thr)
    r = H2.event_test2(d, spec, "btc", horizons=(10, 30, 60), episode_bar=20)
    say(f"\n[{series} {side}] hypothesis {'+' if hyp > 0 else '-'}")
    say(H2.line2(r))
    k = H2.risk_test(d, spec, "btc", windows=(30,), crash=-0.10, episode_bar=20)
    say(H2.risk_line(k))
    for h, e in r["horizons"].items():
        c = e["cell"]
        signs = [np.sign(c[p]["excess"]) if c.get(p, {}).get("excess") is not None else None for p in ("train", "validation", "test")]
        summary.append({"series": series, "side": side, "h": h, "hyp": hyp, "signs": signs, "val_t": c.get("validation", {}).get("t_nw"),
                        "n_ind": (c.get("train", {}).get("n_ind") or 0) + (c.get("validation", {}).get("n_ind") or 0), "verdict": e["verdict"]})
        if e["verdict"].startswith("PASS"):
            passes.append(f"{series} {side} h={h}: {e['verdict']}")
# calibration of the continuous reading, 30d, by decile per period
say("\n== calibration: mean 30d BTC return by decile of the reading (train | validation | test), Spearman ==")
px = d["btc"]; fwd = px.shift(-30) / px - 1
for s in sorted({c[0] for c in CELLS}):
    if s not in d:
        continue
    r = d[s].shift(1)
    parts = []
    for pname in ("train", "validation", "test"):
        m = H2.slice_period(r, pname, "1d"); y = H2.slice_period(fwd, pname, "1d"); ok = m.notna() & y.notna(); m = m[ok]; y = y[ok]
        if len(m) < 100:
            parts.append("-"); continue
        dec = pd.qcut(m.rank(method="first"), 10, labels=False); means = y.groupby(dec).mean()
        rho = float(np.corrcoef(pd.Series(means.values).rank(), np.arange(10))[0, 1])
        parts.append(" ".join(f"{v * 100:+.0f}" for v in means.values) + f" ρ{rho:+.2f}")
    say(f"  {s:16s} " + " | ".join(parts))
say("\n== hypothesis-consistent cells (excess sign = hypothesis in all three periods with data) ==")
for row in summary:
    s = [x for x in row["signs"] if x is not None]
    if len(s) >= 2 and all(x == row["hyp"] for x in s):
        say(f"  {row['series']} {row['side']} h={row['h']}: val t {row['val_t'] and round(row['val_t'], 2)}, n_ind {row['n_ind']} -> {row['verdict'][:70]}")
say("\n== PASSES ==")
say("\n".join(passes) if passes else "none")
open(os.path.join(HERE, "results3", "macro_report.txt"), "w").write("\n".join(lines))
json.dump(summary, open(os.path.join(HERE, "results3", "macro_summary.json"), "w"), indent=1, default=lambda o: None if (isinstance(o, float) and np.isnan(o)) else str(o))
