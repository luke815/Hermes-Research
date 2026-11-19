"""Build base_rates.json: what historically followed each reading's state, with episode counts and period agreement.

This is a DESCRIPTION of the past, not a forecast. Every row carries n days, n independent episodes and whether
the direction agreed across the three research periods. The dashboard looks up the row matching the live state.

Readings (per asset btc/eth), state = quintile of the trailing-365-day percentile (NaN-safe, lag 1):
  funding (perp funding, Laevitas 2019+ where present else dashboard), oi_usd (futures OI, USD), oi_coins (OI / price),
  basis, lsr (long/short ratio), dvol, skew30, ivrv30, price (trailing-365 percentile of price itself: the control).
Targets per state: forward 10/30/60/90-day return (mean, median, p10, p90, excess vs all days), forward 30-day max
drawdown (mean, P(<= -10%), P(<= -20%)), forward 30-day realized vol; per period and pooled.
Also: days-in-state buckets for the top quintile (1-10, 11-30, 31-60, >60) with 30-day targets; state persistence
(P(same quintile after 7/14/30 days)); TD Sequential per timeframe (1D, 3D, 4H, 1H) per flag: n, mean/median forward
5- and 10-bar return and excess; and the setup-count table.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import harness as H  # noqa: E402
import harness2 as H2  # noqa: E402
import harness3 as H3  # noqa: E402

OUT = os.path.join(HERE, "results3", "base_rates.json")
QUINTILES = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0001)]
QLABEL = ["bottom", "low", "mid", "high", "top"]
HORIZONS = (10, 30, 60, 90)
# Caveats and notes come from the pass-3 refutation (results3/refute/, PASS3_2026-11-19.md). They travel with the table.
CAVEATS = {
    "lsr": "The dashboard long/short series stepped up in level in 2021, so its 2021 'top fifth' days are partly an artefact; since mid-2024 a top reading mostly means the price already fell over the past month. A plain 'price down over 30 days' rule reproduces the weaker returns after high readings.",
    "oi_usd": "USD notional open interest is price times coin open interest: four in five top-fifth days are also price-at-a-1-year-high days, and the price row reproduces what follows. It carries no 30-90 day information beyond price.",
    "oi_coins": "Coin open interest at its highs was followed by weak 1-3 month returns only in the 2021-22 bear; nothing since.",
    "funding": "Crowded funding was followed by shallower drawdowns in 2021-25 and by deeper ones in 2026 for ETH; the sign is not stable.",
}
NOTES = [
    {"title": "What was tested", "text": "Three pre-registered passes (PREREG, PREREG2, PREREG3): single and conditioned extremes of funding, open interest, basis, long/short ratio, DVOL, skew and risk reversals by tenor, butterfly, ATM term structure, IV/RV, put/call, at 1-90 days, on returns and on forward drawdowns; time in a crowded state and the exit from it; TD Sequential setups and countdowns on 1H, 4H, 1D and 3D; alt cross-section reversal and momentum. About 1,300 cells. Entry one bar after the signal, three periods, Newey-West errors, independent-episode counts, costs and carry."},
    {"title": "What passed", "text": "Nothing that survived refutation. One drawdown cell passed the rule (ETH daily TD9 buy, 10 days) and is consistent with chance: 4 validation episodes, a random-date placebo passes as often, BTC does not confirm, the sign flips at 20 and 30 days."},
    {"title": "Overheating readings", "text": "At 10-30 days, crowded funding, basis and open interest were followed by shallower drawdowns, not deeper, in 2021-25. At 30-90 days, USD open interest at its highs was followed by weak returns, but that is price at its highs (the control row) plus the 2022 bear. Time already spent in a crowded state did not add information once price duration was controlled; the 2024-25 pattern of long high-OI runs ending in crashes is three episodes (Aug 2024, Feb 2025, Oct 2025)."},
    {"title": "TD Sequential", "text": "TD9 and TD13 completions on daily closes are about as frequent as on a random walk (roughly one per 70 bars). No completion carried the textbook bounce or fade across periods on any timeframe; the daily buy-countdown-13 was followed by further weakness in 18 of 24 episodes in 2019-25, which is too few, too count-specific and already contradicted in 2026 to use. The counts are shown as structure."},
    {"title": "How to read this tab", "text": "A row says what happened after past days in the same fifth, with the number of independent episodes. An 'across periods' badge of consistent means the 30-day direction agreed in 2019-24H1, 2024H2-25 and 2026; it does not mean the reading caused it, and the caveats say where a simpler explanation exists. Rows with fewer than 10 episodes describe a few events."},
]
SOURCES = {"funding": "Laevitas perp funding (2019+), dashboard Binance funding where missing", "oi_usd": "Laevitas futures OI, all venues, USD",
           "oi_coins": "Laevitas futures OI / price", "basis": "dashboard basis", "lsr": "dashboard long/short ratio",
           "dvol": "Deribit DVOL via Laevitas, dashboard where missing", "skew30": "Laevitas 25d skew 30d, dashboard where missing",
           "ivrv30": "Laevitas IV30 / RV30", "price": "spot close"}


def readings(d, a):
    A = a.upper()
    px = H.price(d, a)
    r = {
        # both columns are percent per 8h (checked 2026-11-19: perp_funding_btc equals btc_funding to the digit where both exist)
        "funding": d[f"perp_funding_{a}"].combine_first(d[f"{a}_funding"]) if f"perp_funding_{a}" in d else d[f"{a}_funding"],
        "oi_usd": d[f"futures_oi_{a}"],
        "oi_coins": d[f"futures_oi_{a}"] / px,
        "basis": d[f"basis_{a}"],
        "lsr": d[f"lsr_{A}"],
        "dvol": d[f"dvol_lv_{a}"].combine_first(d[f"dvol_{a}"]) if f"dvol_lv_{a}" in d else d[f"dvol_{a}"],
        "skew30": d[f"skew_30_{a}"].combine_first(d[f"skew_{a}"]) if f"skew_30_{a}" in d else d[f"skew_{a}"],
        "ivrv30": d[f"ivrv30_{a}"],
        "price": px,
    }
    return r


def period_mask(index, pname):
    lo, hi = H.PERIODS[pname]
    m = pd.Series(True, index=index)
    if lo:
        m &= index >= lo
    if hi:
        m &= index <= hi
    return m


def dist(y):
    y = y.dropna()
    if len(y) == 0:
        return None
    return {"mean": float(y.mean()), "median": float(y.median()), "p10": float(y.quantile(0.1)), "p90": float(y.quantile(0.9)), "n": int(len(y))}


def agreement(signs):
    """signs: list of excess signs per period (None when a period has too few episodes)."""
    s = [x for x in signs if x is not None]
    if len(s) < 2:
        return "insufficient"
    if len(s) == 3 and len(set(s)) == 1:
        return "consistent"
    if len(set(s)) == 1:
        return "consistent-2of3"
    return "mixed"


def reading_table(d, a):
    px = H.price(d, a)
    fwd = {h: px.shift(-h) / px - 1 for h in HORIZONS}
    mdd30 = H2.forward_mdd(px, 30)
    rv30 = H2.forward_rv(px, 30, 1)
    out = {}
    for name, s in readings(d, a).items():
        pct = H.pct_rank(s, 365, 180).shift(1)  # known at yesterday's close
        valid = s.dropna()
        entry = {"source_start": str(valid.index[0].date()) if len(valid) else None, "n_days_with_state": int(pct.notna().sum()),
                 "source": SOURCES.get(name, ""), "caveat": CAVEATS.get(name), "states": {}}
        for (lo, hi), label in zip(QUINTILES, QLABEL):
            f = (pct >= lo) & (pct < hi)
            st = {"periods": {}, "pooled": {}}
            signs30 = []
            for pname in H.PERIODS:
                m = period_mask(d.index, pname) & pct.notna()
                row = {"n_days": int((f & m).sum())}
                for h in HORIZONS:
                    y = fwd[h][m]
                    yf = y[f[m]]
                    if yf.notna().sum() >= 3:
                        row[f"ret{h}"] = dist(yf)
                        row[f"ret{h}"]["excess"] = float(yf.mean() - y.mean())
                        row[f"ret{h}"]["n_ind"] = H2.clusters(yf.dropna().index, h, "1d")
                        row[f"ret{h}"]["t_nw"] = H.nw_t(y.dropna().to_numpy(float), f[m][y.notna()].to_numpy(float), h)[0] if y.notna().sum() > h + 5 else None
                m30 = mdd30[m]
                mf = m30[f[m]]
                if mf.notna().sum() >= 3:
                    row["mdd30"] = {"mean": float(mf.mean()), "median": float(mf.median()), "p_le_10": float((mf <= -0.10).mean()),
                                    "p_le_20": float((mf <= -0.20).mean()), "base_p_le_10": float((m30 <= -0.10).mean()),
                                    "base_p_le_20": float((m30 <= -0.20).mean()), "diff": float(mf.mean() - m30.mean())}
                    row["rv30"] = {"flag": float(rv30[m][f[m]].mean()), "all": float(rv30[m].mean())}
                st["periods"][pname] = row
                r30 = row.get("ret30")
                signs30.append(int(np.sign(r30["excess"])) if r30 and r30["n_ind"] >= 3 and r30["excess"] != 0 else None)
            m = pct.notna()
            pooled = {"n_days": int((f & m).sum())}
            for h in HORIZONS:
                y, yf = fwd[h][m], fwd[h][m][f[m]]
                if yf.notna().sum() >= 3:
                    pooled[f"ret{h}"] = dist(yf)
                    pooled[f"ret{h}"]["excess"] = float(yf.mean() - y.mean())
                    pooled[f"ret{h}"]["n_ind"] = H2.clusters(yf.dropna().index, h, "1d")
            mf = mdd30[m][f[m]]
            if mf.notna().sum() >= 3:
                pooled["mdd30"] = {"mean": float(mf.mean()), "median": float(mf.median()), "p_le_10": float((mf <= -0.10).mean()),
                                   "p_le_20": float((mf <= -0.20).mean()), "base_p_le_10": float((mdd30[m] <= -0.10).mean()),
                                   "base_p_le_20": float((mdd30[m] <= -0.20).mean()), "diff": float(mf.mean() - mdd30[m].mean())}
            st["pooled"] = pooled
            st["agreement_ret30"] = agreement(signs30)
            entry["states"][label] = st
        # days-in-state for the top quintile and persistence
        top = pct >= 0.8
        run = H3.days_in_state(top)
        buckets = {}
        for lo, hi, label in ((1, 10, "1-10"), (11, 30, "11-30"), (31, 60, "31-60"), (61, 10 ** 6, ">60")):
            f = (run >= lo) & (run <= hi)
            b = {}
            for pname in list(H.PERIODS) + ["pooled"]:
                m = (period_mask(d.index, pname) if pname != "pooled" else pd.Series(True, index=d.index)) & pct.notna()
                yf, mf = fwd[30][m][f[m]], mdd30[m][f[m]]
                if yf.notna().sum() >= 3:
                    b[pname] = {"n_days": int(f[m].sum()), "n_ind": H2.clusters(yf.dropna().index, 30, "1d"),
                                "ret30_excess": float(yf.mean() - fwd[30][m].mean()), "mdd30_mean": float(mf.mean()),
                                "mdd30_diff": float(mf.mean() - mdd30[m].mean()), "p_le_10": float((mf <= -0.10).mean())}
                else:
                    b[pname] = {"n_days": int(f[m].sum())}
            buckets[label] = b
        entry["top_quintile_duration"] = buckets
        pers = {}
        for k in (7, 14, 30):
            for (lo, hi), label in zip(QUINTILES, QLABEL):
                if label not in ("top", "bottom"):
                    continue
                f = (pct >= lo) & (pct < hi)
                later = f.shift(-k)
                m = f & later.notna()
                pers[f"{label}_still_{label}_after_{k}d"] = float(later[m].mean()) if m.sum() >= 10 else None
        entry["persistence"] = pers
        runs = run[(run > 0) & (run.shift(-1) == 0)]
        entry["top_quintile_runs"] = {"n_runs": int(len(runs)), "median_days": float(runs.median()) if len(runs) else None,
                                      "p90_days": float(runs.quantile(0.9)) if len(runs) else None}
        out[name] = entry
    return out


def td_table(d, h, h4):
    out = {}
    frames = {"1D": [("", d, "1d")], "3D": [(f"a{k}", f, "3d") for k, f in H3_three_day(d)], "4H": [("", h4, "4h")], "1H": [("", h, "1h")]}
    for tf, lst in frames.items():
        out[tf] = {}
        for a in ("btc", "eth"):
            res = {}
            for flag in ("buy9", "sell9", "buy9p", "sell9p", "buy13", "sell13"):
                rows = []
                for fname, frame, freq in lst:
                    px = H.price(frame, a)
                    f = frame[f"td_{flag}_{a}"].shift(1) == 1
                    for hb in (5, 10):
                        y = px.shift(-hb) / px - 1
                        for pname in H2.periods_for(freq):
                            yy = H2.slice_period(y, pname, freq)
                            ff = H2.slice_period(f, pname, freq)
                            yf = yy[ff]
                            if yf.notna().sum() >= 3:
                                rows.append({"frame": fname, "h": hb, "period": pname, "n": int(yf.notna().sum()),
                                             "n_ind": H2.clusters(yf.dropna().index, hb, freq),
                                             "mean": float(yf.mean()), "median": float(yf.median()), "excess": float(yf.mean() - yy.mean())})
                df = pd.DataFrame(rows)
                summ = {}
                if len(df):
                    for hb in (5, 10):
                        for pname in ("train", "validation", "test"):
                            sub = df[(df.h == hb) & (df.period == pname)]
                            if len(sub):
                                summ[f"h{hb}_{pname}"] = {"n": int(sub.n.sum()), "n_ind": int(sub.n_ind.sum()), "excess": float(sub.excess.mean()), "mean": float(sub["mean"].mean())}
                    signs = [int(np.sign(summ[f"h10_{p}"]["excess"])) if f"h10_{p}" in summ and summ[f"h10_{p}"]["n_ind"] >= 3 else None for p in ("train", "validation", "test")]
                    summ["agreement_h10"] = agreement(signs)
                    summ["hypothesis_sign"] = 1 if flag.startswith("buy") else -1
                res[flag] = summ
            # current counts
            fname, frame, freq = lst[0]
            setup = frame[f"td_setup_{a}"].dropna()
            res["current"] = {"setup_count": float(setup.iloc[-1]) if len(setup) else None, "as_of": str(setup.index[-1]) if len(setup) else None}
            out[tf][a] = res
    return out


def H3_three_day(d):
    frames = []
    for anchor in (0, 1, 2):
        d3 = d.iloc[anchor::3].copy()
        for a in ("btc", "eth"):
            H3.td_columns(d3, a)
        frames.append((anchor, d3))
    return frames


def setup_counts(d):
    out = {}
    for a in ("btc", "eth"):
        px = H.price(d, a)
        fwd = px.shift(-10) / px - 1
        setup = d[f"td_setup_{a}"].shift(1)
        out[a] = {}
        for pname in H.PERIODS:
            m = period_mask(d.index, pname) & fwd.notna() & setup.notna()
            y, s = fwd[m], setup[m]
            row = {}
            for grp, label in (((-9, -8, -7), "buy7-9"), ((-6, -5, -4), "buy4-6"), ((-3, -2, -1), "buy1-3"), ((1, 2, 3), "sell1-3"), ((4, 5, 6), "sell4-6"), ((7, 8, 9), "sell7-9")):
                f = s.isin(grp)
                if f.sum() >= 8:
                    row[label] = {"n": int(f.sum()), "excess10": float(y[f].mean() - y.mean()), "t": H.nw_t(y.to_numpy(float), f.to_numpy(float), 10)[0]}
            out[a][pname] = row
    return out


if __name__ == "__main__":
    d = pd.read_pickle(os.path.join(HERE, "data", "daily2.pkl"))
    for a in ("btc", "eth"):
        H3.td_columns(d, a)
    h = pd.read_pickle(os.path.join(HERE, "data", "hourly.pkl"))
    h4 = h.resample("4h").last()
    for a in ("btc", "eth"):
        for frame in (h, h4):
            px = frame[a].dropna()
            td = H3.td_sequential(px)
            for k in td.columns:
                frame[f"td_{k}_{a}"] = td[k].reindex(frame.index).fillna(0.0)
    payload = {
        "generated_from": {"daily": [str(d.index[0].date()), str(d.index[-1].date())], "hourly": [str(h.index[0]), str(h.index[-1])]},
        "periods": {k: list(v) for k, v in H.PERIODS.items()},
        "method": "state = quintile of trailing-365-day percentile known at the prior close (lag 1); excess = mean forward return in state minus mean over all days of the period; n_ind = independent episodes (flagged days more than h days apart); mdd30 = worst close-to-close drawdown within 30 days; agreement = sign of 30-day excess across train/validation/test when each has >= 3 episodes. Description of the past, not a forecast.",
        "readings": {a: reading_table(d, a) for a in ("btc", "eth")},
        "td": td_table(d, h, h4),
        "td_setup_counts": setup_counts(d),
        "notes": NOTES,
    }
    with open(OUT, "w") as fh:
        json.dump(payload, fh, indent=1, default=lambda o: None if (isinstance(o, float) and np.isnan(o)) else (float(o) if isinstance(o, (np.floating,)) else str(o)))
    print("wrote", OUT, os.path.getsize(OUT) // 1024, "KB")
    # quick print: top-quintile 30d outcomes per reading, pooled, with agreement
    for a in ("btc", "eth"):
        print(f"== {a}: top quintile, pooled 30d: excess / median / P(mdd30<=-10%) vs base / n_ind / agreement")
        for name, e in payload["readings"][a].items():
            st = e["states"]["top"]
            p = st["pooled"]
            r = p.get("ret30")
            m = p.get("mdd30")
            if r and m:
                print(f"  {name:9s} ex {r['excess'] * 100:+5.1f}% med {r['median'] * 100:+5.1f}% crash {m['p_le_10']:.2f} vs {m['base_p_le_10']:.2f}  n_ind {r['n_ind']:3d}  {st['agreement_ret30']}")
