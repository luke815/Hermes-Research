"""Write the R1 readings onto the panel and into the risk key.

Every input in research/RISK_REGIME.md section 1 is computed from the
panel and the derivatives store, trailing only. A series the files do not
hold is recorded unavailable rather than filled. The readings become
columns on data/panel.csv, written as a sibling and swapped in. The risk
key gets the same inputs for the last closed day. The results file is
written by this script.
"""

import json
import os
import sys
from datetime import datetime, timezone

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from regime_tester.derivatives import market_measures  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402
from regime_tester.risk import inputs_on, percentile, readings  # noqa: E402
from dashboard_io import write_csv_atomic, write_key  # noqa: E402

PANEL = os.path.join(ROOT, "data", "panel.csv")
OUT = os.path.join(ROOT, "data", "panel_r1.csv")
KEY = os.path.join(ROOT, "dashboard", "keys", "risk.json")

# Section 1 names, and the column the readings frame stores each one in.
# A name whose column is absent, or null on the last day, is unavailable:
# the file that would carry it is not on disk, and a research run does not
# pull it.
SECTION_1 = (
    ("btc_vs_200d", "btc_vs_200d"),
    ("weekly_band", "weekly_position"),
    ("sma50_vs_200d", "sma50_vs_200d"),
    ("alt_vs_200d", "alt_vs_200d"),
    ("alt_vs_50d", "alt_vs_50d"),
    ("eth_btc_30d", "eth_btc_30d"),
    ("alt_vs_btc_30d", "alt_vs_btc_30d"),
    ("rv_30", "rv_30"),
    ("rv_pct", "rv_pct"),
    ("dvol", "dvol"),
    ("dvol_minus_rv", "dvol_minus_rv"),
    ("funding", "funding"),
    ("funding_pct", "funding_pct"),
    ("oi_vs_90d_high", "oi_vs_90d_high"),
    ("oi_change_30d", "oi_change_30d"),
    ("oi_flush", "oi_flush"),
    ("liq_cascade", "liq_cascade"),
    ("basis_pct", "basis_pct"),
    ("breadth_above_50d", "breadth_above_50d"),
    ("breadth_above_200d", "breadth_above_200d"),
    ("funding_crowded_share", "funding_crowded_share"),
    ("stablecoin_supply_30d", "stablecoin_supply_30d"),
    ("etf_flows_20d", "etf_flows_20d"),
    ("exchange_balance", "exchange_balance"),
    ("dxy_30d", "dxy_30d"),
    ("us10y_30d", "us10y_30d"),
    ("btc_ndx_corr_60d", "btc_ndx_corr_60d"),
    ("drawdown_90d", "drawdown_90d"),
    ("drawdown_ath", "drawdown_ath"),
    ("drawdown_alt_90d", "drawdown_alt_90d"),
    ("book_drawdown", "book_drawdown"),
    ("heat", "heat"),
)


def _num(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(number):
        return None
    return number


def enrich(frame):
    """The section-1 readings the base frame does not already carry."""
    out = frame.copy()
    if "alt_price" in frame.columns and "btc_price" in frame.columns:
        alt = frame["alt_price"].astype(float)
        btc = frame["btc_price"].astype(float)
        out["alt_vs_btc_30d"] = (alt / btc).pct_change(30) * 100
    if "dvol" in out.columns and "rv_30" in out.columns:
        out["dvol_minus_rv"] = out["dvol"] - out["rv_30"]
    if "basis_pct" not in out.columns and "basis" in out.columns:
        out["basis_pct"] = percentile(out["basis"])
    return out


def row_inputs(row):
    """One entry per section-1 input, read from the column that holds it.

    The flag comes from inputs_on where that function knows the name. A
    column that is absent or null is unavailable, so a gap is never reported
    as a calm reading.
    """
    known = {item["name"]: item for item in inputs_on(row)}
    ordered = []
    for name, column in SECTION_1:
        value = row.get(column) if column in row else None
        present = value is not None and not (
            isinstance(value, float) and pd.isna(value))
        if not present:
            ordered.append({
                "name": name, "value": None, "pct": None,
                "flag": "unavailable", "effect": "none", "available": False,
            })
            continue
        source = known.get(name) or known.get(column)
        ordered.append({
            "name": name,
            "value": value,
            "pct": None if source is None else source.get("pct"),
            "flag": "computed" if source is None else source.get("flag"),
            "effect": "none" if source is None else source.get("effect"),
            "available": True,
        })
    return ordered


def main():
    panel = pd.read_csv(PANEL, index_col=0, parse_dates=True)
    panel.index = pd.to_datetime(panel.index, utc=True)
    market = market_measures()
    frame = enrich(readings(panel, market))
    added = [name for name in frame.columns if name not in panel.columns]
    merged = panel.join(frame[added], how="left")
    before = set(panel.columns)
    write_csv_atomic(PANEL, merged)
    written = pd.read_csv(PANEL, index_col=0, nrows=0)
    if not set(added).issubset(written.columns):
        raise SystemExit("the panel write did not land")
    if not before.issubset(written.columns):
        raise SystemExit("the panel write dropped a column")
    last = merged.dropna(subset=["btc_price"]).index.max()
    row = {k: (None if pd.isna(v) else v) for k, v in frame.loc[last].items()}
    items = row_inputs(row)
    for item in items:
        item["value"] = _num(item["value"]) if item["available"] else None
        item["pct"] = _num(item["pct"])
    key = {
        "as_of": last.strftime("%Y-%m-%d"),
        "inputs": items,
        "note": (
            "R1 readings. A series not on disk is unavailable, not filled. "
            "The dial and the backtest belong to later items."),
    }
    write_key(KEY, key)
    payload = {
        "item": "R1",
        "as_of": key["as_of"],
        "panel_rows": int(len(merged)),
        "panel_out": "data/panel.csv",
        "columns_added": added,
        "inputs": [
            {"name": item["name"], "value": item["value"],
             "pct": item["pct"], "flag": item["flag"],
             "available": item["available"]}
            for item in items],
        "available_count": sum(1 for item in items if item["available"]),
        "unavailable": [item["name"] for item in items if not item["available"]],
    }
    path = write_result("r1_inputs", payload, inputs=[
        "data/panel.csv", "data/laevitas/market"])
    print(path)
    print(json.dumps({
        "as_of": payload["as_of"],
        "available": payload["available_count"],
        "unavailable": payload["unavailable"],
        "columns_added": added,
    }))


if __name__ == "__main__":
    main()
