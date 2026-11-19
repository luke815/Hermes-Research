"""Merge the Laevitas CSVs into data/daily2.pkl (daily, joined to the dashboard panel) and data/hourly.pkl.

Column names produced (per asset A in {btc, eth}):
  skew_{7,14,30,60,90,180,365}_A, rr_*_A, bf_*_A (butterfly), atmiv_*_A, dvol_lv_A, ivrv_A (first numeric column),
  pc_ratio_A, options_oi_A, futures_oi_A, perp_funding_A, perp_oi_A
  derived: skew_slope_A = skew_7 - skew_90; atm_slope_A = atmiv_7 - atmiv_90; atm_inv_A = (atm_slope > 0);
           ivrv_ratio_A = atmiv_30 / rv_A when rv is in the dashboard file (rv_btc, rv_eth)
Hourly columns: close_A, volume_A, dvol_lv_A, skew_*_A, rr_*_A, atmiv_*_A, perp_funding_A, perp_oi_A.
Rows are UTC; daily rows are stamped at 00:00 and joined to the dashboard date index; the Laevitas daily sample for
day D is taken as known at the close of day D (it is a midnight sample at the START of D, so this is conservative).
"""

from __future__ import annotations

import glob
import os
import re

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
LAE = os.path.join(HERE, "data", "laevitas")
OUT_D = os.path.join(HERE, "data", "daily2.pkl")
OUT_H = os.path.join(HERE, "data", "hourly.pkl")


def read(path):
    df = pd.read_csv(path)
    col = "date" if "date" in df.columns else df.columns[0]
    ts = df[col]
    if pd.api.types.is_numeric_dtype(ts):
        ts = pd.to_datetime(ts, unit="ms" if ts.max() > 1e11 else "s", utc=True)
    else:
        ts = pd.to_datetime(ts.astype(str), utc=True, format="mixed")
    df = df.drop(columns=[col]).apply(pd.to_numeric, errors="coerce")
    df.index = ts
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df


def tenor_cols(df, prefix, asset):
    out = {}
    for c in df.columns:
        m = re.fullmatch(r"(\d+)", str(c))
        if m:
            out[f"{prefix}_{m.group(1)}_{asset}"] = df[c]
    if not out and len(df.columns) >= 1:
        out[f"{prefix}_{asset}"] = df.iloc[:, 0]
    return pd.DataFrame(out)


def build(freq):
    suffix = "_1d.csv" if freq == "1d" else "_1h.csv"
    frames = []
    for path in sorted(glob.glob(os.path.join(LAE, f"*{suffix}"))):
        name = os.path.basename(path)[: -len(suffix)]
        asset = "btc" if name.endswith("_BTC") else "eth" if name.endswith("_ETH") else None
        if "coinbase" in name:
            continue
        if asset is None:
            continue
        kind = name[: -4]
        df = read(path)
        if kind == "options_skew25":
            frames.append(tenor_cols(df, "skew", asset))
        elif kind == "options_rr25":
            frames.append(tenor_cols(df, "rr", asset))
        elif kind == "options_bf25":
            frames.append(tenor_cols(df, "bf", asset))
        elif kind == "options_atmiv":
            frames.append(tenor_cols(df, "atmiv", asset))
        elif kind == "options_dvol":
            frames.append(pd.DataFrame({f"dvol_lv_{asset}": df.iloc[:, 0]}))
        elif kind == "options_ivrv":
            cols = {f"lv_iv_{c[3:]}_{asset}": df[c] for c in df.columns if c.startswith("iv_")}
            cols.update({f"lv_rv_{c[3:]}_{asset}": df[c] for c in df.columns if c.startswith("rv_")})
            if "iv_30" in df.columns and "rv_30" in df.columns:
                cols[f"ivrv30_{asset}"] = df["iv_30"] / df["rv_30"].replace(0, np.nan)
                cols[f"vrp30_{asset}"] = df["iv_30"] - df["rv_30"]
            frames.append(pd.DataFrame(cols))
        elif kind == "pos_pcratio":
            col = "pc" if "pc" in df.columns else df.columns[-1]
            frames.append(pd.DataFrame({f"pc_ratio_{asset}": df[col]}))
        elif kind == "pos_options_oi":
            frames.append(pd.DataFrame({f"options_oi_{asset}": df.iloc[:, 0]}))
        elif kind == "pos_futures_oi":
            frames.append(pd.DataFrame({f"futures_oi_{asset}": df.iloc[:, 0]}))
        elif kind == "perp_funding":
            frames.append(pd.DataFrame({f"perp_funding_{asset}": df.iloc[:, 0]}))
        elif kind == "perp_oi":
            frames.append(pd.DataFrame({f"perp_oi_{asset}": df.iloc[:, 0]}))
        elif kind == "price":
            frames.append(pd.DataFrame({f"close_{asset}": df["close"], f"volume_{asset}": df.get("volume")}))
    if not frames:
        raise SystemExit(f"no {freq} CSVs under {LAE}")
    panel = pd.concat(frames, axis=1, sort=True)
    if freq == "1d":
        panel.index = panel.index.normalize().tz_localize(None)
        panel = panel[~panel.index.duplicated(keep="last")]
        base = pd.read_pickle(os.path.join(HERE, "data", "daily.pkl"))
        early = os.path.join(HERE, "data", "spot_2019.pkl")  # BTC/ETH closes before the dashboard file starts
        if os.path.exists(early):
            ext = pd.read_pickle(early)
            ext = ext[ext.index < base.index[0]]
            base = pd.concat([ext.reindex(columns=base.columns), base]).sort_index()
        panel = base.join(panel, how="left")
    else:
        panel.index = panel.index.tz_localize(None)
        panel = panel.resample("1h").last()
    for a in ("btc", "eth"):
        if f"skew_7_{a}" in panel and f"skew_90_{a}" in panel:
            panel[f"skew_slope_{a}"] = panel[f"skew_7_{a}"] - panel[f"skew_90_{a}"]
        if f"atmiv_7_{a}" in panel and f"atmiv_90_{a}" in panel:
            panel[f"atm_slope_{a}"] = panel[f"atmiv_7_{a}"] - panel[f"atmiv_90_{a}"]
            panel[f"atm_inv_{a}"] = (panel[f"atm_slope_{a}"] > 0).astype(float).where(panel[f"atm_slope_{a}"].notna())
        if freq == "1d" and f"atmiv_30_{a}" in panel and f"rv_{a}" in panel:
            panel[f"ivrv_ratio_{a}"] = panel[f"atmiv_30_{a}"] / panel[f"rv_{a}"]
        if freq == "1h" and f"close_{a}" in panel:
            panel[a] = panel[f"close_{a}"]  # so harness.price(df, "btc") works on hourly data
            if f"perp_funding_{a}" in panel:
                panel[f"{a}_funding"] = panel[f"perp_funding_{a}"] * 100  # harness.funding divides by 100
    if freq == "1d":
        # prefer Laevitas perp series where present, but keep the dashboard columns the harness already uses
        pass
    out = OUT_D if freq == "1d" else OUT_H
    panel.to_pickle(out)
    return panel


if __name__ == "__main__":
    for freq in ("1d", "1h"):
        try:
            p = build(freq)
            cov = p.notna().sum()
            print(f"{freq}: {len(p)} rows {p.index[0]} -> {p.index[-1]}, {len(p.columns)} columns")
            print(cov[cov > 0].sort_values().head(12).to_string())
        except SystemExit as exc:
            print(exc)
