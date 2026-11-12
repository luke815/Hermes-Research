"""Universe ranking. The composite on every name with enough history.

Equal weights, the same six components as the book. A name that fails a long or
short rule gets the first reason it failed, so the table shows why it is not a
leg. Writes the universe_rank key of dashboard/data.json.

Usage: python3 scripts/universe_rank.py
"""

import json
import os
from datetime import datetime, timezone

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs")
DATA = os.path.join(ROOT, "dashboard", "data.json")


def score_name(frame):
    close = frame["close"].dropna()
    if len(close) < 50:
        return None
    last = close.iloc[-1]
    rs_14 = last / close.iloc[-15] - 1 if len(close) > 15 else None
    rs_30 = last / close.iloc[-31] - 1 if len(close) > 31 else None
    ma20 = close.iloc[-20:].mean()
    ma50 = close.iloc[-50:].mean()
    high = close.iloc[-252:].max() if len(close) >= 252 else close.max()
    low = close.iloc[-252:].min() if len(close) >= 252 else close.min()
    range_pos = (last - low) / (high - low) if high > low else None
    funding = frame["funding_rate"].dropna() if "funding_rate" in frame else pd.Series(dtype=float)
    funding_pct = float((funding.iloc[-252:] <= funding.iloc[-1]).mean()) if len(funding) > 30 else None
    parts = [v for v in (rs_14, rs_30, range_pos) if v is not None]
    return {
        "rs_14": round(rs_14 * 100, 1) if rs_14 is not None else None,
        "rs_30": round(rs_30 * 100, 1) if rs_30 is not None else None,
        "range_pos": round(range_pos, 3) if range_pos is not None else None,
        "funding_pct": round(funding_pct, 3) if funding_pct is not None else None,
        "score": round(sum(parts) / len(parts), 4) if parts else None,
        "above_both": bool(last > ma20 and last > ma50),
        "below_both": bool(last < ma20 and last < ma50),
    }


def main():
    rows = []
    for name in sorted(os.listdir(PANEL)):
        frame = pd.read_csv(os.path.join(PANEL, name))
        scored = score_name(frame)
        if not scored or scored["score"] is None:
            continue
        symbol = name.replace(".csv", "").split("_", 1)[-1].replace("USDT", "").replace("-SWAP", "")
        long_ok = scored["above_both"] and (scored["funding_pct"] is None or scored["funding_pct"] < 0.8)
        short_ok = scored["below_both"] and scored["funding_pct"] is not None and scored["funding_pct"] >= 0.5
        reasons = ""
        if not long_ok and not short_ok:
            reasons = "below both averages" if not scored["above_both"] else "funding crowded"
        rows.append({"symbol": symbol, "score": scored["score"], "rs_14": scored["rs_14"],
                     "rs_30": scored["rs_30"], "range_pos": scored["range_pos"],
                     "funding_pct": scored["funding_pct"], "long_ok": long_ok,
                     "short_ok": short_ok, "reasons": reasons})
    rows.sort(key=lambda r: r["score"], reverse=True)
    n = len(rows)
    for i, row in enumerate(rows):
        row["decile"] = min(10, i * 10 // n + 1)
    payload = {"as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
               "note": "Equal weights. Relative strength, range position and funding percentile.",
               "rows": rows}
    data = json.load(open(DATA))
    data["universe_rank"] = payload
    tmp = DATA + ".tmp"
    json.dump(data, open(tmp, "w"))
    os.replace(tmp, DATA)
    print(f"ranked {n} names, top {rows[0]['symbol']} {rows[0]['score']}, "
          f"bottom {rows[-1]['symbol']} {rows[-1]['score']}")


if __name__ == "__main__":
    main()
