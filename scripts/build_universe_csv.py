"""Point-in-time universe from the three span tables.

One row per name and exchange: first bar, last bar, whether the name has been
delisted, and the delisting date when it has. Binance's span table carries no
delisted flag, so a Binance name whose last bar is more than 14 days before
today is marked delisted on the evidence of the span itself, and the row says
so. OKX symbols are stored without the USDT suffix; they are normalised here.

Usage: python3 scripts/build_universe_csv.py
"""

import os
from datetime import datetime, timezone, timedelta

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "universe.csv")
STALE_DAYS = 14


def load(exchange, path, suffix):
    frame = pd.read_csv(os.path.join(ROOT, path))
    frame["exchange"] = exchange
    frame["symbol"] = frame["symbol"].astype(str) + suffix
    return frame


def main():
    today = datetime.now(timezone.utc).date()
    cutoff = (today - timedelta(days=STALE_DAYS)).isoformat()
    frames = [
        load("binance", "data/binance_span.csv", ""),
        load("bybit", "data/bybit_span.csv", ""),
        load("okx", "data/okx_span.csv", "-USDT-SWAP"),
    ]
    rows = []
    for frame in frames:
        has_flag = "stopped" in frame.columns
        for _, row in frame.iterrows():
            last = str(row["last"])
            if has_flag:
                delisted = int(row["stopped"]) == 1
                basis = "span_flag"
            else:
                delisted = last < cutoff
                basis = "last_bar_stale"
            rows.append({
                "exchange": row["exchange"],
                "symbol": row["symbol"],
                "first_bar": str(row["first"]),
                "last_bar": last,
                "delisted": int(delisted),
                "delisting_date": last if delisted else "",
                "delisted_basis": basis if delisted else "",
            })
    out = pd.DataFrame(rows).sort_values(["exchange", "symbol"])
    tmp = OUT + ".tmp"
    out.to_csv(tmp, index=False)
    os.replace(tmp, OUT)
    print(f"names {len(out)} listed {int((out['delisted'] == 0).sum())} "
          f"delisted {int(out['delisted'].sum())}")
    print(f"first {out['first_bar'].min()} last {out['last_bar'].max()}")
    print(out.groupby("exchange")["delisted"].agg(["count", "sum"]).to_string())


if __name__ == "__main__":
    main()
