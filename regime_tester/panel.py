"""Combine Coinalyze positioning data with Laevitas basis into one daily panel.

Writes data/panel.csv: one row per day, factors for BTC, ETH, and an alt basket.
The basis is the mean across venues for the 90-day tenor, which is what the
research notes settled on after dropping the noisy 12.5 and 15 thresholds.
"""

import json
from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT = Path(__file__).resolve().parent.parent / "data" / "panel.csv"


def load_coinalyze(blob: str, field: str) -> pd.DataFrame:
    frames = []
    for path in sorted(RAW.glob(blob)):
        payload = json.loads(path.read_text())
        inverse = {v: k for k, v in payload["symbols"].items()}
        columns = {}
        for series in payload["data"]:
            token = inverse[series["symbol"]]
            columns[token] = pd.Series(
                {bar["t"]: bar.get(field) for bar in series["history"]}, dtype=float
            )
        frame = pd.DataFrame(columns).sort_index()
        frame.index = pd.to_datetime(frame.index, unit="s", utc=True)
        frames.append(frame)
    if not frames:
        raise FileNotFoundError(blob)
    return pd.concat(frames).groupby(level=0).last().sort_index()


def load_basis(token: str) -> pd.Series:
    rows = []
    for path in sorted(RAW.glob(f"basis_{token.lower()}*.json")):
        rows.extend(json.loads(path.read_text()))
    by_date = {}
    for row in rows:
        venues = [v for k, v in row.items() if k != "date" and isinstance(v, (int, float))]
        if venues:
            by_date[row["date"]] = sum(venues) / len(venues)
    series = pd.Series(by_date, dtype=float).sort_index()
    series.index = pd.to_datetime(series.index, unit="ms", utc=True)
    return series.rename(f"basis_{token.lower()}")


def build() -> pd.DataFrame:
    oi = load_coinalyze("coinalyze_open-interest*.json", "c")
    price = load_coinalyze("coinalyze_ohlcv*.json", "c")
    funding = load_coinalyze("coinalyze_funding*.json", "c")

    total_oi = oi.sum(axis=1)
    alt_oi = oi.drop(columns="BTC").sum(axis=1)
    spread = ((alt_oi - oi["BTC"]) / total_oi).rename("oi_spread")

    # OI-weighted funding across the alt basket. BTC and ETH funding are perps.
    alt_weights = oi.drop(columns=["BTC", "ETH"])
    alt_fund = funding.drop(columns=["BTC", "ETH"]).reindex(alt_weights.index)
    weighted = (alt_fund * alt_weights).sum(axis=1) / alt_weights.sum(axis=1)
    alt_funding = weighted.rename("alt_funding")

    btc_share = (oi["BTC"] / total_oi).rename("btc_oi_share")

    panel = pd.concat([
        price["BTC"].rename("btc_price"),
        price["ETH"].rename("eth_price"),
        funding["BTC"].rename("btc_funding"),
        funding["ETH"].rename("eth_funding"),
        alt_funding,
        spread,
        btc_share,
        load_basis("BTC"),
        load_basis("ETH"),
    ], axis=1).sort_index()

    # equal-weight alt basket price, for scoring the regime against the market
    alt_prices = price.drop(columns=["BTC", "ETH"])
    panel["alt_price"] = (1 + alt_prices.pct_change().mean(axis=1).fillna(0)).cumprod()

    # dispersion: how far apart the alts are moving. High dispersion preceded
    # stronger alt returns in both halves and is only moderately tied to momentum.
    panel["dispersion_14"] = alt_prices.pct_change(14).std(axis=1)
    # only rows where price and funding are both present; a partial day is not a day
    return panel.dropna(subset=["btc_price", "btc_funding"])


if __name__ == "__main__":
    from datetime import datetime, timezone
    panel = build()
    tmp = OUT.with_suffix(".csv.tmp")
    panel.to_csv(tmp)
    tmp.replace(OUT)
    today = datetime.now(timezone.utc).date()
    last = panel.dropna(subset=["btc_price"]).index.max().date()
    age = (today - last).days
    print(f"today {today}  panel ends {last}  age {age} days")
    if age > 2:
        raise SystemExit(f"STALE: panel is {age} days behind")
