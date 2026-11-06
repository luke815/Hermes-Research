"""Point-in-time cross-sectional panel, one daily file per name.

Built from the stores on disk. A name with no stored history gets a file that
records the gap rather than one filled with invented rows. Price, volume,
funding and open interest are joined on the date where each exists and left
empty where it does not.

The stores currently hold the delisted names only. The listed names' history
has not been pulled, and this script does not pull it.

Usage: python3 scripts/build_panel_xs.py
"""

import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "panel_xs")

STORES = {
    ("binance", "price"): ("data/binance_prices", ["date", "close", "volume"]),
    ("binance", "funding"): ("data/binance_funding", ["date", "funding_rate"]),
    ("binance", "oi"): ("data/binance_metrics", ["date", "oi_usd"]),
    ("okx", "price"): ("data/okx_prices", ["date", "close", "vol_quote"]),
    ("okx", "funding"): ("data/okx_funding", ["date", "funding_rate"]),
}


def store_name(exchange, symbol, kind):
    """The filename a store uses for this name, which differs by exchange."""
    if exchange == "okx":
        return symbol.split("-")[0]
    return symbol


def read_store(exchange, symbol, kind):
    directory, columns = STORES[(exchange, kind)]
    path = os.path.join(ROOT, directory, store_name(exchange, symbol, kind) + ".csv")
    if not os.path.exists(path):
        return None
    frame = pd.read_csv(path, usecols=lambda c: c in columns)
    frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%d")
    return frame


def main():
    os.makedirs(OUT, exist_ok=True)
    universe = pd.read_csv(os.path.join(ROOT, "data", "universe.csv"))
    written, with_price, empty = 0, 0, 0
    for _, name in universe.iterrows():
        exchange, symbol = name["exchange"], name["symbol"]
        frames = []
        price = read_store(exchange, symbol, "price") if (exchange, "price") in STORES else None
        if price is not None:
            price = price.rename(columns={"vol_quote": "volume_usd", "volume": "volume_base"})
            frames.append(price)
        for kind, column in (("funding", "funding_rate"), ("oi", "oi_usd")):
            if (exchange, kind) not in STORES:
                continue
            part = read_store(exchange, symbol, kind)
            if part is not None:
                frames.append(part)
        out_name = f"{exchange}_{symbol}.csv"
        if not frames:
            pd.DataFrame(columns=["date", "close", "volume_usd", "funding_rate", "oi_usd"]).to_csv(
                os.path.join(OUT, out_name), index=False)
            empty += 1
        else:
            merged = frames[0]
            for part in frames[1:]:
                merged = merged.merge(part, on="date", how="outer")
            merged = merged.sort_values("date")
            merged.to_csv(os.path.join(OUT, out_name), index=False)
            if "close" in merged.columns and merged["close"].notna().any():
                with_price += 1
        written += 1
        if written % 500 == 0:
            print(f"wrote {written}", flush=True)
    print(f"files {written} with_price {with_price} empty {empty}")


if __name__ == "__main__":
    main()
