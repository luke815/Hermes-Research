"""Rewrite panel_xs so funding is the daily sum and every file is sorted.

The funding stores keep the last settlement of the day plus the count of
settlements, or the day's mean. The sum is last times count for Binance and
mean times count for OKX. Bybit has no funding store, so its files are only
sorted. One row per base coin is counted here; the readers collapse on load.

Writes results/<today>_a1_integrity.json.
"""

import json
import os
import sys
from datetime import datetime, timezone
from glob import glob

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.panel_integrity import base_of, clean_frame  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs")
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def funding_sum(exchange, symbol):
    """Daily sum and interval for one name, or None when no store exists."""
    if exchange == "binance":
        path = os.path.join(ROOT, "data", "binance_funding", f"{symbol}.csv")
        if not os.path.exists(path):
            return None
        store = pd.read_csv(path)
        store["funding_rate"] = store["funding_rate"] * store["settlements"]
        store["funding_interval_hours"] = (24 / store["settlements"]).round().astype(int)
        return store.set_index("date")[["funding_rate", "funding_interval_hours"]]
    if exchange == "okx":
        stem = symbol.split("-")[0]
        path = os.path.join(ROOT, "data", "okx_funding", f"{stem}.csv")
        if not os.path.exists(path):
            return None
        store = pd.read_csv(path)
        store["funding_rate"] = store["funding_mean"] * store["settlements"]
        store["funding_interval_hours"] = (24 / store["settlements"]).round().astype(int)
        return store.set_index("date")[["funding_rate", "funding_interval_hours"]]
    return None


def rewrite():
    resorted, funding_rewritten = [], []
    for path in sorted(glob(os.path.join(PANEL, "*.csv"))):
        name = os.path.basename(path)
        exchange, symbol = name.split("_", 1)
        symbol = symbol[:-4]
        frame = pd.read_csv(path)
        before = list(frame["date"].astype(str)) if "date" in frame.columns else []
        summed = funding_sum(exchange, symbol)
        if summed is not None and "date" in frame.columns:
            frame = frame.drop(columns=[c for c in ("funding_rate", "funding_interval_hours")
                                        if c in frame.columns])
            frame = frame.merge(summed, left_on="date", right_index=True, how="left")
            funding_rewritten.append(name)
        cleaned = clean_frame(frame, today=TODAY)
        after = list(cleaned["date"].astype(str)) if "date" in cleaned.columns else []
        if before != after or name in funding_rewritten:
            resorted.append(name)
        tmp = path + ".tmp"
        cleaned.to_csv(tmp, index=False)
        os.replace(tmp, path)
    return resorted, funding_rewritten


def venue_collapse():
    """How many file names a one-row-per-coin read drops, and on how many dates."""
    rows = []
    for path in sorted(glob(os.path.join(PANEL, "*.csv"))):
        frame = pd.read_csv(path, usecols=lambda c: c in ("date", "volume_usd", "volume_base"))
        if frame.empty or "date" not in frame.columns:
            continue
        volume = frame["volume_usd"] if "volume_usd" in frame.columns else frame.get("volume_base")
        rows.append(pd.DataFrame({
            "date": frame["date"].astype(str),
            "base": base_of(os.path.basename(path).split("_", 1)[1][:-4]),
            "volume": pd.to_numeric(volume, errors="coerce").fillna(-1.0),
        }))
    stacked = pd.concat(rows, ignore_index=True)
    per_date = stacked.groupby(["base", "date"]).size()
    dates_collapsed = int((per_date > 1).sum())
    names = stacked["base"].nunique()
    return {"files": int(stacked.groupby("base").ngroups and len(glob(os.path.join(PANEL, "*.csv")))),
            "base_coins": int(names),
            "names_collapsed": int(len(glob(os.path.join(PANEL, "*.csv"))) - names),
            "date_rows_collapsed": dates_collapsed}


def main():
    resorted, funding_rewritten = rewrite()
    collapse = venue_collapse()
    out = {
        "date": TODAY,
        "files_rewritten": len(resorted),
        "files_resorted": resorted,
        "funding_sum_files": len(funding_rewritten),
        "funding_sum_names": funding_rewritten,
        "venue_collapse": collapse,
    }
    dest = os.path.join(ROOT, "results", f"{TODAY}_a1_integrity.json")
    json.dump(out, open(dest, "w"), indent=1)
    print(json.dumps({"date": TODAY, "files_rewritten": len(resorted),
                      "funding_sum_files": len(funding_rewritten),
                      "venue_collapse": collapse}))


if __name__ == "__main__":
    main()
