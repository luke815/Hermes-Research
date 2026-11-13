"""D1 slice: daily bars for stopped Bybit names with 501 to 550 listed days.

Bound: stopped == 1 and 500 < listed day count <= 550 in data/bybit_span.csv.
Each day is one raw-trade gzip, reduced to one bar. Days of one name download
in parallel; the part file is written before the next day is counted, so an
interrupted run resumes.
"""

import csv
import gzip
import io
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPAN = ROOT / "data" / "bybit_span.csv"
PARTS = ROOT / "data" / "bybit_price_parts"
OUT = ROOT / "data" / "bybit_prices"
LO = 500
HI = 550
WORKERS = 8
BASE = ["timestamp", "symbol", "side", "size", "price", "tickDirection", "trdMatchID", "grossValue", "homeNotional", "foreignNotional"]
BAR = "date,open,high,low,close,volume,quote,trades"


def names():
    only = set(sys.argv[1:])
    out = []
    with SPAN.open(newline="") as fh:
        for row in csv.DictReader(fh):
            days = int(row["days"])
            if row["stopped"] == "1" and LO < days <= HI and (not only or row["symbol"] in only):
                out.append(row)
    out.sort(key=lambda r: (int(r["days"]), r["symbol"]))
    return out


def listing(symbol):
    url = f"https://public.bybit.com/trading/{symbol}/"
    req = urllib.request.Request(url, headers={"User-Agent": "regime-tester"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        text = resp.read().decode("utf-8", "replace")
    dates = []
    needle = f'href="{symbol}'
    for line in text.splitlines():
        if needle in line and ".csv.gz" in line:
            start = line.index(needle) + len('href="')
            name = line[start:line.index('"', start)]
            dates.append(name[len(symbol):-len(".csv.gz")])
    return sorted(dates)


def reduce_day(symbol, day):
    url = f"https://public.bybit.com/trading/{symbol}/{symbol}{day}.csv.gz"
    req = urllib.request.Request(url, headers={"User-Agent": "regime-tester"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        raw = resp.read()
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as gz:
            header = gz.readline().decode("utf-8", "replace").strip()
            if not header:
                return empty(day)
            cols = header.split(",")
            if cols[:len(BASE)] != BASE:
                raise ValueError(f"header mismatch {symbol} {day}: {cols}")
            first_ts = last_ts = None
            open_px = high = low = close_px = None
            volume = quote = 0.0
            trades = 0
            for line in gz:
                row = line.decode("utf-8", "replace").rstrip("\n").split(",")
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
    except EOFError:
        return empty(day)
    if trades == 0:
        return empty(day)
    return {
        "date": day, "open": open_px, "high": high, "low": low, "close": close_px,
        "volume": volume, "quote": quote, "trades": trades,
    }


def empty(day):
    return {
        "date": day, "open": "", "high": "", "low": "", "close": "",
        "volume": 0, "quote": 0, "trades": 0, "empty_archive": True,
    }


def write_part(symbol, bar):
    path = PARTS / f"{symbol}_{bar['date']}.csv"
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(BAR.split(","))
        w.writerow([bar[k] for k in BAR.split(",")])


def fetch_one(symbol, day):
    part = PARTS / f"{symbol}_{day}.csv"
    if part.exists() and part.stat().st_size > 0:
        return day, None, "skip"
    last = None
    for attempt in range(3):
        try:
            bar = reduce_day(symbol, day)
            write_part(symbol, bar)
            return day, bar, None
        except (urllib.error.URLError, TimeoutError, ConnectionError, EOFError) as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
        except Exception as exc:  # noqa: BLE001
            return day, None, exc
    return day, None, last


def write_symbol(symbol, dates):
    rows = []
    for day in dates:
        with (PARTS / f"{symbol}_{day}.csv").open(newline="") as fh:
            rows.append(next(csv.DictReader(fh)))
    rows.sort(key=lambda r: r["date"])
    path = OUT / f"{symbol}.csv"
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=BAR.split(","))
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def main():
    PARTS.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    chosen = names()
    report = {"date": today, "bound": f"{LO} < days <= {HI}", "names": [], "failures": [], "empty": []}
    print(f"BOUND {len(chosen)} names days {sum(int(r['days']) for r in chosen)} workers {WORKERS}", flush=True)
    for row in chosen:
        symbol = row["symbol"]
        try:
            dates = listing(symbol)
        except Exception as exc:  # noqa: BLE001
            report["failures"].append({"symbol": symbol, "stage": "listing", "error": str(exc)})
            print(f"LISTING FAIL {symbol} {exc}", flush=True)
            continue
        pending = [d for d in dates if not ((PARTS / f"{symbol}_{d}.csv").exists() and (PARTS / f"{symbol}_{d}.csv").stat().st_size > 0)]
        print(f"START {symbol} listed={len(dates)} pending={len(pending)}", flush=True)
        done = len(dates) - len(pending)
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futures = [pool.submit(fetch_one, symbol, day) for day in pending]
            for fut in as_completed(futures):
                day, bar, err = fut.result()
                if err is not None:
                    report["failures"].append({"symbol": symbol, "day": day, "error": str(err)})
                    print(f"FAIL {symbol} {day} {err}", flush=True)
                    continue
                done += 1
                if bar and bar.get("empty_archive"):
                    report["empty"].append({"symbol": symbol, "date": day})
                if done % 25 == 0 or done == len(dates):
                    print(f"PROGRESS {symbol} {done}/{len(dates)}", flush=True)
        saved = write_symbol(symbol, dates) if done == len(dates) and dates else 0
        report["names"].append({
            "symbol": symbol,
            "span_first": row["first"],
            "span_last": row["last"],
            "span_days": int(row["days"]),
            "listed_days": len(dates),
            "saved_days": saved,
            "match": saved == int(row["days"]) == len(dates),
        })
        print(f"NAME {symbol} listed={len(dates)} saved={saved} span={row['days']}", flush=True)
    tag = "_".join(sys.argv[1:]) or "all"
    out = ROOT / "results" / f"{today}_d1_bybit_prices_501_550_{tag}.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"WROTE {out}", flush=True)
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
