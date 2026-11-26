"""Alt long/short board: the pre-registered ranking (research/outside/ALT_LS_PREREG.md), its weekly ledger and its
measured history. Writes dashboard/keys/ls_board.json (the assembler copies it into data.json), appends to
results/ls_ledger.csv, and writes a stamped results file through write_result when regime_tester is importable.

Rule (fixed before any number was computed, see the pre-registration):
  universe   names in data/panel_xs with 365 closes, listed today, crypto only, OI >= $20M and volume >= $15M where
             data/universe.csv carries those columns (the floor is skipped, and said so, where it does not)
  signal     rs30 = 30-day return minus BTC's 30-day return, at the close
  crowding   fund_pct = trailing-365-day percentile of the funding rate
  longs      top decile by rs30 with fund_pct < 0.8 (not crowded)
  shorts     bottom decile by rs30 with fund_pct > 0.2 (not already washed out)
  hold       entered at the next close after the Monday close, equal weight, held 7 days; costs 30 bps round trip per
             name plus funding carry by side
  history    every Monday with 365 days behind it: top minus bottom decile forward 7-day relative return, filtered and
             unfiltered, train <= 2024-06-30 / validation 2024-07-01..2025-12-31 / test 2026, weekly rows so the t is
             on non-overlapping observations

Usage: python scripts/alt_ls_board.py [--mode xs|dashboard] [--asof YYYY-MM-DD]
  xs         Hermes's point-in-time panel (data/panel_xs/<venue>_<SYMBOL>USDT.csv with date, close, funding_rate, ...)
  dashboard  the 18-alt dashboard series in dashboard/data.json (the fallback used for the first run off the box)
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
PANEL = os.path.join(ROOT, "data", "panel_xs")
UNIVERSE = os.path.join(ROOT, "data", "universe.csv")
DASH = os.path.join(ROOT, "dashboard", "data.json")
KEY = os.path.join(ROOT, "dashboard", "keys", "ls_board.json")
LEDGER = os.path.join(ROOT, "results", "ls_ledger.csv")
PERIODS = {"train": (None, "2024-06-30"), "validation": ("2024-07-01", "2025-12-31"), "test": ("2026-01-01", None)}
COST_RT = 0.003  # 30 bps round trip per name, the alt tier
HOLD = 7
TRADFI = re.compile(r"^(XYZ:|.*(SPX|SP500|NDX|GOLD|XAU|XAG|OIL|CL|NATGAS|TSLA|NVDA|AAPL|MSTR|COIN|HOOD|AMZN|GOOG|META|EUR|GBP|JPY)$)")


def is_crypto(symbol):
    try:
        from universe_rank import is_crypto as _ic  # Hermes's own denylist when present
        return _ic(symbol)
    except Exception:
        return not TRADFI.match(symbol)


def load_xs():
    """Close, funding and OI matrices from data/panel_xs; one column per symbol (venue dropped, first file wins)."""
    closes, fundings, ois, files = {}, {}, {}, []
    for path in sorted(glob.glob(os.path.join(PANEL, "*.csv"))):
        name = os.path.basename(path)[:-4]
        sym = name.split("_", 1)[1] if "_" in name else name
        sym = re.sub(r"USDT$", "", sym)
        if sym in closes or not is_crypto(sym):
            continue
        f = pd.read_csv(path)
        if "date" not in f or "close" not in f:
            continue
        f["date"] = pd.to_datetime(f["date"])
        f = f.drop_duplicates("date").set_index("date").sort_index()
        if f["close"].notna().sum() < 365:
            continue
        closes[sym] = f["close"].astype(float)
        fcol = next((c for c in ("funding_rate", "funding") if c in f), None)
        if fcol:
            fundings[sym] = f[fcol].astype(float)
        ocol = next((c for c in ("open_interest", "oi_usd", "oi") if c in f), None)
        if ocol:
            ois[sym] = f[ocol].astype(float)
        files.append(os.path.relpath(path, ROOT))
    btc = closes.pop("BTC", None)
    if btc is None:
        raise SystemExit("no BTC file in the panel")
    closes.pop("ETH", None)
    liquid = None
    if os.path.exists(UNIVERSE):
        u = pd.read_csv(UNIVERSE)
        scol = next((c for c in ("symbol", "name") if c in u), None)
        ocol = next((c for c in ("oi_usd", "open_interest_usd", "oi") if c in u), None)
        vcol = next((c for c in ("volume_usd", "vol_usd", "volume", "vol") if c in u), None)
        if scol and ocol:
            u["_sym"] = u[scol].astype(str).str.replace(r"USDT.*$", "", regex=True).str.split("_").str[-1]
            ok = u[ocol].astype(float) >= 20e6
            if vcol:
                ok &= u[vcol].astype(float) >= 15e6
            liquid = set(u.loc[ok, "_sym"])
            files.append(os.path.relpath(UNIVERSE, ROOT))
    return btc, pd.DataFrame(closes), pd.DataFrame(fundings), pd.DataFrame(ois), liquid, files


def load_dashboard():
    d = json.load(open(DASH))
    S = d["series"]
    idx = pd.to_datetime(S["date"])
    btc = pd.Series(S["btc"], index=idx, dtype=float)
    closes = {k[6:]: pd.Series(v, index=idx, dtype=float) for k, v in S.items() if k.startswith("price_")}
    fundings = {k[8:]: pd.Series(v, index=idx, dtype=float) for k, v in S.items() if k.startswith("funding_") and k[8:] in closes}
    ois = {k[3:]: pd.Series(v, index=idx, dtype=float) for k, v in S.items() if k.startswith("oi_") and k[3:] in closes}
    return btc, pd.DataFrame(closes), pd.DataFrame(fundings), pd.DataFrame(ois), None, [os.path.relpath(DASH, ROOT)]


def pct_rank_last(s, window=365, min_periods=180):
    """Share of the previous window values at or below the last value (the panel's convention)."""
    v = s.dropna().to_numpy(float)
    if len(v) < min_periods + 1:
        return np.nan
    past = v[-window - 1:-1]
    return float((past <= v[-1]).mean())


def signals_at(closes, fund, oi, btc, t):
    """Cross-sectional readings known at close t."""
    c = closes.loc[:t]
    if len(c) < 31:
        return None
    r30 = c.iloc[-1] / c.iloc[-31] - 1
    b30 = btc.loc[:t].iloc[-1] / btc.loc[:t].iloc[-31] - 1
    r7 = c.iloc[-1] / c.iloc[-8] - 1
    b7 = btc.loc[:t].iloc[-1] / btc.loc[:t].iloc[-8] - 1
    out = pd.DataFrame({"rs30": r30 - b30, "rs7": r7 - b7})
    if len(fund.columns):
        f = fund.loc[:t]
        out["fund_pct"] = pd.Series({s: pct_rank_last(f[s]) for s in f.columns if s in out.index})
        out["fund_last"] = f.iloc[-1].reindex(out.index)
    if len(oi.columns):
        o = oi.loc[:t]
        out["oi_chg30"] = (o.iloc[-1] / o.iloc[-31] - 1).reindex(out.index) if len(o) > 31 else np.nan
    return out[out["rs30"].notna()]


def select(sig, min_names=3):
    n = len(sig)
    k = max(min_names, int(round(n / 10)))
    ranked = sig.sort_values("rs30", ascending=False)
    top, bottom = ranked.head(k), ranked.tail(k)
    fp = sig.get("fund_pct")
    longs = top[(top["fund_pct"].isna()) | (top["fund_pct"] < 0.8)] if fp is not None else top
    shorts = bottom[(bottom["fund_pct"].isna()) | (bottom["fund_pct"] > 0.2)] if fp is not None else bottom
    return longs, shorts, top, bottom


def forward_rel(closes, btc, t, h=HOLD):
    """Relative return from the close after t over h days (entry lag 1), per name; NaN when the window is open."""
    pos = closes.index.get_loc(t)
    if pos + 1 + h >= len(closes):
        return None
    e, x = closes.iloc[pos + 1], closes.iloc[pos + 1 + h]
    be, bx = btc.iloc[pos + 1], btc.iloc[pos + 1 + h]
    return (x / e - 1) - (bx / be - 1)


def carry(fund, t, names, h=HOLD):
    """Funding paid (longs) or received (shorts) over the hold: funding is percent per 8h in the panel (0.01 = 1 bp)."""
    if not len(fund.columns):
        return pd.Series(0.0, index=names)
    pos = fund.index.get_loc(t) if t in fund.index else None
    if pos is None:
        return pd.Series(0.0, index=names)
    w = fund.iloc[pos + 1:pos + 1 + h].reindex(columns=names)
    return (w.sum(min_count=1) / 100 * 3).fillna(0.0)  # percent per 8h -> fraction, three settlements a day summed over the days


def nw_t(x):
    x = np.asarray([v for v in x if v == v], float)
    if len(x) < 5:
        return None
    m = x.mean(); e = x - m; n = len(x)
    var = (e @ e) / n
    for lag in range(1, 2):  # weekly rows are non-overlapping; one lag for safety
        wgt = 1 - lag / 2
        var += 2 * wgt * (e[:-lag] @ e[lag:]) / n
    return float(m / np.sqrt(var / n)) if var > 0 else None


def history(closes, fund, oi, btc):
    """Weekly top-minus-bottom decile spreads, filtered and unfiltered, net of costs and carry."""
    mondays = [t for t in closes.index if t.weekday() == 0]
    rows = []
    for t in mondays:
        if (t - closes.index[0]).days < 365:
            continue
        sig = signals_at(closes, fund, oi, btc, t)
        if sig is None or len(sig) < 6:
            continue
        rel = forward_rel(closes, btc, t)
        if rel is None:
            continue
        longs, shorts, top, bottom = select(sig)
        def basket(names, side):
            if not len(names):
                return np.nan
            r = rel.reindex(names.index).dropna()
            if not len(r):
                return np.nan
            c = carry(fund, t, list(r.index))
            gross = r.mean() * side
            return float(gross - COST_RT - (c.mean() * side))
        uni = rel.reindex(sig.index).dropna()
        rows.append({"week": t.date().isoformat(), "n": len(sig), "long_raw": basket(top, 1), "short_raw": basket(bottom, -1),
                     "long": basket(longs, 1), "short": basket(shorts, -1), "n_long": len(longs), "n_short": len(shorts),
                     "universe_mean": float(uni.mean()) if len(uni) else np.nan})  # the control: every name in the universe vs BTC, gross
    h = pd.DataFrame(rows)
    if not len(h):
        return {"weeks": 0}
    h["spread_raw"] = h["long_raw"] + h["short_raw"]
    h["spread"] = h["long"] + h["short"]
    out = {"weeks": int(len(h)), "first_week": h["week"].iloc[0], "last_week": h["week"].iloc[-1], "periods": {}}
    for pname, (lo, hi) in PERIODS.items():
        m = pd.Series(True, index=h.index)
        if lo:
            m &= h["week"] >= lo
        if hi:
            m &= h["week"] <= hi
        s = h[m]
        if len(s) < 4:
            out["periods"][pname] = {"weeks": int(len(s))}
            continue
        out["periods"][pname] = {
            "weeks": int(len(s)),
            "spread_mean": float(s["spread"].mean()), "spread_t": nw_t(s["spread"]), "spread_hit": float((s["spread"] > 0).mean()),
            "long_mean": float(s["long"].mean()), "long_hit": float((s["long"] > 0).mean()),
            "short_mean": float(s["short"].mean()), "short_hit": float((s["short"] > 0).mean()),
            "spread_raw_mean": float(s["spread_raw"].mean()), "spread_raw_t": nw_t(s["spread_raw"]),
            "worst_week": float(s["spread"].min()), "best_week": float(s["spread"].max()),
            # control: the average name vs BTC over the same weeks; a short basket only shows selection if it beats shorting the average
            "universe_mean": float(s["universe_mean"].mean()), "universe_hit_below_zero": float((s["universe_mean"] < 0).mean()),
            "short_vs_universe": float((s["short"] - (-s["universe_mean"] - COST_RT)).mean()),
            "long_vs_universe": float((s["long"] - (s["universe_mean"] - COST_RT)).mean()),
        }
    signs = [np.sign(p.get("spread_mean", 0)) for p in out["periods"].values() if p.get("weeks", 0) >= 4]
    out["agreement"] = "consistent" if len(signs) == 3 and len(set(signs)) == 1 and signs[0] != 0 else "mixed"
    return out


def update_ledger(asof, longs, shorts, closes, fund, btc):
    """Append this week's lists; fill realized outcomes for rows whose hold has ended."""
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    rows = []
    if os.path.exists(LEDGER):
        with open(LEDGER) as fh:
            rows = list(csv.DictReader(fh))
    have = {(r["week"], r["side"], r["symbol"]) for r in rows}
    for side, names in (("long", longs), ("short", shorts)):
        for sym, r in names.iterrows():
            if (asof, side, sym) not in have:
                rows.append({"week": asof, "side": side, "symbol": sym, "rs30": f"{r['rs30']:.4f}", "fund_pct": "" if pd.isna(r.get("fund_pct", np.nan)) else f"{r['fund_pct']:.3f}",
                             "rel_ret_7d": "", "abs_ret_7d": "", "filled_at": ""})
    for r in rows:
        if r["rel_ret_7d"]:
            continue
        t = pd.Timestamp(r["week"])
        if t not in closes.index or r["symbol"] not in closes.columns:
            continue
        rel = forward_rel(closes, btc, t)
        if rel is None or pd.isna(rel.get(r["symbol"], np.nan)):
            continue
        pos = closes.index.get_loc(t)
        c = closes[r["symbol"]]
        r["rel_ret_7d"] = f"{rel[r['symbol']]:.4f}"
        r["abs_ret_7d"] = f"{c.iloc[pos + 1 + HOLD] / c.iloc[pos + 1] - 1:.4f}"
        r["filled_at"] = closes.index[pos + 1 + HOLD].date().isoformat()
    with open(LEDGER, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["week", "side", "symbol", "rs30", "fund_pct", "rel_ret_7d", "abs_ret_7d", "filled_at"])
        w.writeheader(); w.writerows(rows)
    filled = [r for r in rows if r["rel_ret_7d"]]
    def side_stats(side):
        v = [float(r["rel_ret_7d"]) * (1 if side == "long" else -1) for r in filled if r["side"] == side]
        return {"n": len(v), "mean_rel": float(np.mean(v)) if v else None, "hit": float(np.mean([x > 0 for x in v])) if v else None}
    weeks = sorted({r["week"] for r in filled})
    return {"rows": len(rows), "filled": len(filled), "weeks_filled": len(weeks), "long": side_stats("long"), "short": side_stats("short")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("xs", "dashboard"), default="xs" if os.path.isdir(PANEL) else "dashboard")
    ap.add_argument("--asof", default=None)
    a = ap.parse_args()
    btc, closes, fund, oi, liquid, inputs = load_xs() if a.mode == "xs" else load_dashboard()
    closes = closes.dropna(how="all")
    if liquid is not None:
        keep = [c for c in closes.columns if c in liquid]
        closes = closes[keep]
    fund = fund.reindex(columns=[c for c in closes.columns if c in fund.columns]).reindex(closes.index)
    oi = oi.reindex(columns=[c for c in closes.columns if c in oi.columns]).reindex(closes.index)
    btc = btc.reindex(closes.index).ffill()
    asof = pd.Timestamp(a.asof) if a.asof else closes.index[-1]
    sig = signals_at(closes, fund, oi, btc, asof)
    longs, shorts, top, bottom = select(sig)
    hist = history(closes, fund, oi, btc)
    last_monday = max([t for t in closes.index if t.weekday() == 0 and t <= asof])
    sig_m = signals_at(closes, fund, oi, btc, last_monday)
    lm_longs, lm_shorts, _, _ = select(sig_m)
    ledger = update_ledger(last_monday.date().isoformat(), lm_longs, lm_shorts, closes, fund, btc)
    def rows(df):
        return [{"symbol": s, "rs30": round(float(r["rs30"]) * 100, 2), "rs7": round(float(r["rs7"]) * 100, 2),
                 "fund_pct": None if pd.isna(r.get("fund_pct", np.nan)) else round(float(r["fund_pct"]), 2),
                 "fund_bps_8h": None if pd.isna(r.get("fund_last", np.nan)) else round(float(r["fund_last"]) * 100, 2),
                 "oi_chg30": None if pd.isna(r.get("oi_chg30", np.nan)) else round(float(r["oi_chg30"]) * 100, 1)} for s, r in df.iterrows()]
    payload = {
        "as_of": asof.date().isoformat(), "universe": int(len(sig)), "mode": a.mode,
        "liquidity_floor": "OI >= $20M and volume >= $15M from data/universe.csv" if liquid is not None else "none (the 18-alt dashboard universe or no universe.csv)",
        "rule": "top decile by 30-day return vs BTC with funding percentile < 0.8 = long; bottom decile with funding percentile > 0.2 = short; entered the close after the Monday close, equal weight, held 7 days; 30 bps round trip per name plus funding carry",
        "prereg": "research/outside/ALT_LS_PREREG.md",
        "longs": rows(longs), "shorts": rows(shorts), "decile_size": int(len(top)),
        "excluded": {"longs_crowded": [s for s in top.index if s not in longs.index], "shorts_washed": [s for s in bottom.index if s not in shorts.index]},
        "history": hist, "ledger": {**ledger, "week": last_monday.date().isoformat()},
        "note": "A ranking with its measured record, not a signal. The history is the rule applied every Monday since the first week with a year of data; the ledger is the live record from the first week this script ran.",
    }
    os.makedirs(os.path.dirname(KEY), exist_ok=True)
    with open(KEY, "w") as fh:
        json.dump(payload, fh, indent=1)
    try:
        from regime_tester.results_io import write_result
        path = write_result("ls_board", payload, inputs=inputs or [os.path.relpath(DASH, ROOT)])
    except Exception as exc:  # off the box, or an older checkout
        path = os.path.join(ROOT, "results", f"{datetime.now(timezone.utc).date().isoformat()}_ls_board.unstamped.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            json.dump({**payload, "unstamped_reason": str(exc)[:200]}, fh, indent=1)
    print(json.dumps({"as_of": payload["as_of"], "universe": payload["universe"], "longs": [r["symbol"] for r in payload["longs"]],
                      "shorts": [r["symbol"] for r in payload["shorts"]], "history_weeks": hist.get("weeks"),
                      "periods": {k: {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items()} for k, v in hist.get("periods", {}).items()},
                      "agreement": hist.get("agreement"), "ledger": ledger, "key": os.path.relpath(KEY, ROOT), "result": os.path.relpath(path, ROOT)}, indent=1))


if __name__ == "__main__":
    main()
