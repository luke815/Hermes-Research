"""Pull the free flow and macro series (plan item P1 of research/OBJECTIVE_2026-11-19.md) and publish them to the dashboard.

Sources, no keys needed:
  FRED CSV endpoint  https://fred.stlouisfed.org/graph/fredgraph.csv?id=<ID>
      DTWEXBGS broad dollar index, DFII10 10y real yield, WALCL Fed balance sheet (weekly), SP500, NASDAQCOM, VIXCLS, DGS10
  DefiLlama          https://stablecoins.llama.fi/stablecoincharts/all?stablecoin=<1|2>   (1 = USDT, 2 = USDC) circulating supply
Writes data/macro/<ID>.csv and data/macro/usdt.json, usdc.json (raw), then merges five daily readings into the dashboard
file under series.macro_* aligned to the panel dates (forward-filled over weekends), with a units line each:
  macro_stable_supply   USDT + USDC circulating, USD
  macro_dxy             broad dollar index level
  macro_real10          10y real yield, percent
  macro_spx             S&P 500 close
  macro_vix             VIX close
Spot BTC ETF flows are NOT here: Farside blocks scripted reads and CoinGlass needs a key (see OBJECTIVE P1).
Run daily after the panel build. Registered with data_guard.record_write so the health check does not flag the rewrite.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
OUT = os.path.join(ROOT, "data", "macro")
DASH = os.path.join(ROOT, "dashboard", "data.json")
FRED = {"DTWEXBGS": "macro_dxy", "DFII10": "macro_real10", "WALCL": "macro_fed_bs", "SP500": "macro_spx",
        "NASDAQCOM": "macro_ndx", "VIXCLS": "macro_vix", "DGS10": "macro_us10y"}
UNITS = {"macro_stable_supply": "USDT + USDC circulating, USD (DefiLlama)", "macro_dxy": "FRED DTWEXBGS, index level",
         "macro_real10": "FRED DFII10, percent", "macro_fed_bs": "FRED WALCL, millions USD, weekly forward-filled",
         "macro_spx": "FRED SP500 close", "macro_ndx": "FRED NASDAQCOM close", "macro_vix": "FRED VIXCLS close",
         "macro_us10y": "FRED DGS10, percent"}


def fetch(url, path, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "hermes-macro-pull/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    if len(data) < 200:
        raise RuntimeError(f"{url}: {len(data)} bytes")
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def fred_series(fid):
    f = pd.read_csv(os.path.join(OUT, fid + ".csv"))
    f.columns = ["date", "v"]
    f["v"] = pd.to_numeric(f["v"], errors="coerce")
    return pd.Series(f["v"].values, index=pd.to_datetime(f["date"])).dropna()


def llama_series(name):
    j = json.load(open(os.path.join(OUT, name + ".json")))
    s = pd.Series({pd.Timestamp(time.strftime("%Y-%m-%d", time.gmtime(int(r["date"])))): r["totalCirculating"]["peggedUSD"] for r in j})
    return s[~s.index.duplicated(keep="last")].sort_index()


def main():
    os.makedirs(OUT, exist_ok=True)
    for fid in FRED:
        fetch(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={fid}", os.path.join(OUT, fid + ".csv"))
    for name, sid in (("usdt", 1), ("usdc", 2)):
        fetch(f"https://stablecoins.llama.fi/stablecoincharts/all?stablecoin={sid}", os.path.join(OUT, name + ".json"))
    dash = json.load(open(DASH))
    dates = pd.to_datetime(dash["series"]["date"])
    out = {}
    for fid, key in FRED.items():
        s = fred_series(fid)
        out[key] = s.reindex(dates.union(s.index)).ffill().reindex(dates)
    out["macro_stable_supply"] = (llama_series("usdt") + llama_series("usdc")).reindex(dates)
    series = {k: [None if pd.isna(x) else float(x) for x in v.values] for k, v in out.items()}
    try:
        from dashboard_io import locked, read, write_atomic
        with locked(DASH):  # read-modify-write under the dashboard lock so no other writer's keys are lost
            cur = read(DASH)
            cur.setdefault("series", {}).update(series)
            cur["macro_units"] = UNITS
            cur.setdefault("meta", {}).setdefault("as_of", {})["macro"] = pd.Timestamp.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            write_atomic(DASH, cur)
    except ImportError:  # older checkout without dashboard_io: write in place
        dash["series"].update(series)
        dash["macro_units"] = UNITS
        json.dump(dash, open(DASH, "w"))
    try:
        from data_guard import record_write
        record_write("macro_pull", [DASH] + [os.path.join(OUT, f) for f in os.listdir(OUT)], "daily macro and stablecoin pull")
    except Exception:
        pass
    last = {k: (v.dropna().index[-1].date().isoformat(), float(v.dropna().iloc[-1])) for k, v in out.items()}
    print(json.dumps({"written": list(series), "last": last}, default=str))


if __name__ == "__main__":
    main()
