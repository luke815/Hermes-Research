"""Universe table and panel_xs from the Laevitas perpetual store.

One row per instrument in data/laevitas/instruments.json whose type is
perpetual. First bar and last bar are the earliest and latest dates in the
stored file, not the catalogue. A name is delisted when its last bar is more
than 14 days before today, and the row says so. A file with no bars is kept
in the table with empty dates and no panel file.

The old panel_xs is the Binance archive panel the daily append writes. This
writes data/panel_xs_laevitas and data/universe_laevitas.csv, and does not
touch either of those.

Usage: python3 scripts/build_universe_laevitas.py
"""

import hashlib
import json
import os
from datetime import datetime, timezone, timedelta

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "data", "laevitas", "perpetuals")
INSTRUMENTS = os.path.join(ROOT, "data", "laevitas", "instruments.json")
OUT_CSV = os.path.join(ROOT, "data", "universe_laevitas.csv")
OUT_PANEL = os.path.join(ROOT, "data", "panel_xs_laevitas")
STALE_DAYS = 14
JUMP = 50
COLUMNS = ["date", "close", "volume_usd", "volume_base", "funding_rate", "oi_usd",
           "basis", "long_short_ratio"]


def day(millis):
    return datetime.fromtimestamp(millis / 1000, timezone.utc).strftime("%Y-%m-%d")


def closes_of(items, jump=JUMP):
    """One close per item, taken from the index when the price field jumps.

    The vendor price field and the index beside it agree on an ordinary day,
    apart from the contract's own multiplier: a 1000-coin contract prints a
    price about a thousand times its index every day. A day where the price
    field moves by `jump` or more against the day before, while the index
    does not, is the vendor changing unit for one bar. From the first such
    day the close is the price field divided by the ratio of that day, which
    puts that one bar back on the scale the rest of the file uses. A series
    with no index keeps the price field, and the first bar has no prior day.
    """
    ordered = sorted(
        (item for item in items if item.get("price") is not None),
        key=lambda item: item["date"])
    closes = []
    prior_price = None
    prior_index = None
    for item in ordered:
        price, index = item.get("price"), item.get("index")
        price_moved = (
            prior_price and price
            and (price / prior_price >= jump or prior_price / price >= jump))
        index_held = (
            prior_index and index
            and (1 / jump) < (index / prior_index) < jump)
        if price_moved and index_held and price and index:
            closes.append(index)
        else:
            closes.append(price)
            prior_price = price
        prior_index = index
    return closes


def main():
    today = datetime.now(timezone.utc).date()
    cutoff = (today - timedelta(days=STALE_DAYS)).isoformat()
    perps = [r for r in json.load(open(INSTRUMENTS)) if r["type"] == "perpetual"]
    os.makedirs(OUT_PANEL, exist_ok=True)
    rows = []
    written = 0
    empty = 0
    for row in perps:
        path = os.path.join(STORE, f"{row['market']}_{row['instrument']}.json")
        body = json.load(open(path))
        items = [i for i in body.get("items", []) if i.get("price") is not None]
        items.sort(key=lambda i: i["date"])
        if not items:
            empty += 1
            rows.append({
                "exchange": row["market"].lower(),
                "symbol": row["instrument"],
                "currency": row.get("currency") or "",
                "first_bar": "",
                "last_bar": "",
                "bars": 0,
                "delisted": "",
                "delisting_date": "",
                "delisted_basis": "no_bars",
            })
            continue
        first, last = day(items[0]["date"]), day(items[-1]["date"])
        delisted = last < cutoff
        basis = ""
        if delisted and "pages_fetched" not in body:
            basis = "truncated_refetching"
            delisted = False
        elif delisted:
            basis = "last_bar_stale"
        frame = pd.DataFrame({
            "date": [day(i["date"]) for i in items],
            "close": closes_of(items),
            "volume_usd": [i.get("volume") for i in items],
            "volume_base": [i.get("volume_coin") for i in items],
            "funding_rate": [i.get("funding") for i in items],
            "oi_usd": [i.get("open_interest") for i in items],
            "basis": [i.get("basis") for i in items],
            "long_short_ratio": [i.get("long_short_ratio") for i in items],
        })
        frame = frame.drop_duplicates("date").sort_values("date")
        out_name = f"{row['market'].lower()}_{row['instrument']}.csv"
        tmp = os.path.join(OUT_PANEL, out_name + ".tmp")
        frame.to_csv(tmp, index=False)
        os.replace(tmp, os.path.join(OUT_PANEL, out_name))
        written += 1
        rows.append({
            "exchange": row["market"].lower(),
            "symbol": row["instrument"],
            "currency": row.get("currency") or "",
            "first_bar": first,
            "last_bar": last,
            "bars": int(len(frame)),
            "delisted": int(delisted),
            "delisting_date": last if delisted else "",
            "delisted_basis": basis,
        })
        if written % 500 == 0:
            print(f"wrote {written}", flush=True)
    out = pd.DataFrame(rows).sort_values(["exchange", "symbol"])
    tmp = OUT_CSV + ".tmp"
    out.to_csv(tmp, index=False)
    os.replace(tmp, OUT_CSV)
    digest = hashlib.sha256(open(OUT_CSV, "rb").read()).hexdigest()
    listed = int((out["delisted"] == 0).sum())
    delisted_n = int((out["delisted"] == 1).sum())
    print(f"names {len(out)} with_bars {written} empty {empty} "
          f"listed {listed} delisted {delisted_n}")
    print(f"first {out.loc[out['first_bar'] != '', 'first_bar'].min()} "
          f"last {out['last_bar'].max()}")
    print(f"sha256 {digest}")
    print(f"today {today.isoformat()} cutoff {cutoff}")
    print(out.groupby("exchange")["delisted"].apply(
        lambda s: pd.Series({"count": int(len(s)),
                              "listed": int((s == 0).sum()),
                              "delisted": int((s == 1).sum()),
                              "no_bars": int(s.eq("").sum())})
    ).unstack().to_string())


if __name__ == "__main__":
    main()
