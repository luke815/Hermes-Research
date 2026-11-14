"""Reduce pending Bybit days for one symbol, one day at a time.

Each gzip is written to disk before it is reduced, and the part file is
written before the gzip is deleted, so an interrupted run resumes from the
last finished day. A day that fails stays on disk and is retried next run.
"""

import csv
import gzip
import sys
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPAN = ROOT / "data" / "bybit_span.csv"
PARTS = ROOT / "data" / "bybit_price_parts"
RAW = ROOT / "data" / "bybit_raw_tmp"
BASE = ["timestamp", "symbol", "side", "size", "price", "tickDirection", "trdMatchID", "grossValue", "homeNotional", "foreignNotional"]
BAR = ["date", "open", "high", "low", "close", "volume", "quote", "trades"]


def span_of(symbol):
    with SPAN.open(newline="") as fh:
        for row in csv.DictReader(fh):
            if row["symbol"] == symbol:
                return row
    raise SystemExit(f"{symbol} not in span")


def missing(symbol, first, last):
    have = {p.name[len(symbol) + 1:-4] for p in PARTS.glob(f"{symbol}_*.csv")}
    out = []
    d = date.fromisoformat(first)
    end = date.fromisoformat(last)
    while d <= end:
        if d.isoformat() not in have:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def download(symbol, day):
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / f"{symbol}{day}.csv.gz"
    if path.exists() and path.stat().st_size > 0:
        return path
    url = f"https://public.bybit.com/trading/{symbol}/{symbol}{day}.csv.gz"
    req = urllib.request.Request(url, headers={"User-Agent": "regime-tester"})
    tmp = path.with_suffix(".part")
    with urllib.request.urlopen(req, timeout=300) as resp, tmp.open("wb") as fh:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)
    tmp.rename(path)
    return path


def reduce_gz(path, day):
    with gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="") as fh:
        header = fh.readline().strip()
        cols = header.split(",")
        if cols[:len(BASE)] != BASE:
            raise ValueError(f"header mismatch {day}: {cols}")
        first_ts = last_ts = None
        open_px = high = low = close_px = None
        volume = quote = 0.0
        trades = 0
        for line in fh:
            row = line.rstrip("\n").split(",")
            if len(row) < 10 or row[0] == "timestamp":
                continue
            ts = int(float(row[0]))
            px = float(row[4])
            size = float(row[3])
            foreign = float(row[9])
            if first_ts is None or ts < first_ts:
                first_ts = ts
                open_px = px
            if last_ts is None or ts >= last_ts:
                last_ts = ts
                close_px = px
            high = px if high is None else max(high, px)
            low = px if low is None else min(low, px)
            volume += size
            quote += foreign
            trades += 1
    if trades == 0:
        return [day, "", "", "", "", 0, 0, 0]
    return [day, open_px, high, low, close_px, volume, quote, trades]


def main():
    symbol = sys.argv[1]
    row = span_of(symbol)
    todo = missing(symbol, row["first"], row["last"])
    print(f"PENDING {symbol} {len(todo)}", flush=True)
    for day in todo:
        t = time.time()
        path = download(symbol, day)
        vals = reduce_gz(path, day)
        part = PARTS / f"{symbol}_{day}.csv"
        with part.open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(BAR)
            w.writerow(vals)
        path.unlink()
        print(f"SAVED {symbol} {day} trades={vals[7]} sec={time.time()-t:.0f}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
