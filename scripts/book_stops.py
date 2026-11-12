"""The 1.5 ATR spread stop, applied to the open book.

A leg closes when its loss from entry exceeds 1.5 times its own 14-day average
true range, measured on the daily closes. The close is written back to
signals/book.csv with the mark that triggered it, and the leg is not reopened
by the next rebalance.

Usage: python3 scripts/book_stops.py
"""

import json
import os
from datetime import datetime, timezone

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "signals", "book.csv")
PANEL = os.path.join(ROOT, "data", "panel_xs")
STOP_ATR = 1.5


def atr(symbol):
    path = os.path.join(PANEL, f"binance_{symbol}USDT.csv")
    if not os.path.exists(path):
        return None
    frame = pd.read_csv(path)
    close = frame["close"].dropna()
    if len(close) < 15:
        return None
    return float(close.diff().abs().iloc[-14:].mean())


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    book = pd.read_csv(LEDGER)
    if "closed" not in book.columns:
        book["closed"] = ""
        book["close_price"] = None
    closed_now = []
    for i, row in book.iterrows():
        if row.get("closed"):
            continue
        band = atr(row["symbol"])
        if band is None or not row["price"]:
            continue
        # The mark comes from the latest live.json the daemon pushed.
        live = json.load(open(os.path.join(ROOT, "dashboard", "live.json"))) if os.path.exists(
            os.path.join(ROOT, "dashboard", "live.json")) else {}
        marks = {l["symbol"]: l["mark"] for l in (live.get("book_live") or {}).get("legs", [])}
        mark = marks.get(row["symbol"])
        if mark is None:
            continue
        loss = (row["price"] - mark) / row["price"] if row["side"] == "long" else (mark - row["price"]) / row["price"]
        stop = STOP_ATR * band / row["price"]
        if loss > stop:
            book.loc[i, "closed"] = today
            book.loc[i, "close_price"] = mark
            closed_now.append({"symbol": row["symbol"], "side": row["side"], "entry": row["price"],
                               "mark": mark, "loss_pct": round(loss * 100, 2),
                               "stop_pct": round(stop * 100, 2)})
    tmp = LEDGER + ".tmp"
    book.to_csv(tmp, index=False)
    os.replace(tmp, LEDGER)
    print(json.dumps({"closed": closed_now, "open": int((book["closed"] == "").sum())}))


if __name__ == "__main__":
    main()
