"""D1 slice: daily bars for stopped Bybit names with 201 to 250 listed days.

Bound: stopped == 1 and 200 < listed day count <= 250 in data/bybit_span.csv.
Each day is one raw-trade gzip, streamed and reduced to one bar. The part file
is written before the next day starts, so an interrupted run resumes.
"""

import csv
import gzip
import io
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPAN = ROOT / "data" / "bybit_span.csv"
PARTS = ROOT / "data" / "bybit_price_parts"
OUT = ROOT / "data" / "bybit_prices"
LO = 200
HI = 250
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
    print(f"BOUND {len(chosen)} names days {sum(int(r['days']) for r in chosen)}", flush=True)
    for row in chosen:
        symbol = row["symbol"]
        try:
            dates = listing(symbol)
        except Exception as exc:  # noqa: BLE001
            report["failures"].append({"symbol": symbol, "stage": "listing", "error": str(exc)})
            print(f"LISTING FAIL {symbol} {exc}", flush=True)
            continue
        done = 0
        for day in dates:
            part = PARTS / f"{symbol}_{day}.csv"
            if part.exists() and part.stat().st_size > 0:
                done += 1
                continue
            for attempt in range(3):
                try:
                    bar = reduce_day(symbol, day)
                    write_part(symbol, bar)
                    done += 1
                    if bar.get("empty_archive"):
                        report["empty"].append({"symbol": symbol, "date": day})
                    print(f"OK {symbol} {day} trades={bar['trades']}", flush=True)
                    break
                except (urllib.error.URLError, TimeoutError, ConnectionError, EOFError) as exc:
                    print(f"RETRY {symbol} {day} {attempt} {exc}", flush=True)
                    time.sleep(2 * (attempt + 1))
                    if attempt == 2:
                        report["failures"].append({"symbol": symbol, "day": day, "error": str(exc)})
                        print(f"FAIL {symbol} {day} {exc}", flush=True)
                except Exception as exc:  # noqa: BLE001
                    report["failures"].append({"symbol": symbol, "day": day, "error": str(exc)})
                    print(f"FAIL {symbol} {day} {exc}", flush=True)
                    break
            time.sleep(0.15)
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
    out = ROOT / "results" / f"{today}_d1_bybit_prices_201_250_{tag}.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"WROTE {out}", flush=True)
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
