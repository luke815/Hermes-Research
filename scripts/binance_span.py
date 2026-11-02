"""First and last kline date per Binance USDT perp, fetched in parallel.

Writes one row per symbol to data/span_parts/ as soon as it arrives, so a
killed run resumes from the parts already on disk. The listing is paginated;
a single page stops at about 500 days and reports a false last date, so the
marker is followed to the end.
"""

import csv
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester/data")
SYMBOLS = ROOT / "binance_symbols.txt"
PARTS = ROOT / "span_parts"
OUT = ROOT / "binance_span.csv"
NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
BASE = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"


def span(symbol: str) -> tuple[str, str, int]:
    prefix = f"data/futures/um/daily/klines/{symbol}/1d/"
    marker = ""
    first = last = ""
    count = 0
    while True:
        query = "prefix=" + urllib.parse.quote(prefix, safe="/") + "&max-keys=1000"
        if marker:
            query += "&marker=" + urllib.parse.quote(marker, safe="")
        with urllib.request.urlopen(f"{BASE}?{query}", timeout=90) as response:
            root = ET.fromstring(response.read())
        for key in root.findall("s3:Contents/s3:Key", NS):
            name = key.text or ""
            if name.endswith(".zip"):
                date = name.split("-1d-")[-1][:10]
                first = first or date
                last = date
                count += 1
        if root.findtext("s3:IsTruncated", default="false", namespaces=NS) != "true":
            break
        contents = root.findall("s3:Contents/s3:Key", NS)
        marker = root.findtext("s3:NextMarker", default="", namespaces=NS) or (
            contents[-1].text if contents else "")
        if not marker:
            break
    return first, last, count


def one(symbol: str) -> str:
    target = PARTS / f"{symbol}.csv"
    if target.exists():
        return symbol
    first, last, days = span(symbol)
    target.write_text(f"{symbol},{first},{last},{days}\n")
    return symbol


def main() -> None:
    PARTS.mkdir(exist_ok=True)
    symbols = SYMBOLS.read_text().split()
    pending = [s for s in symbols if not (PARTS / f"{s}.csv").exists()]
    print(f"{len(symbols)} symbols, {len(symbols) - len(pending)} done, {len(pending)} left", flush=True)
    finished = 0
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(one, symbol) for symbol in pending]
        for future in as_completed(futures):
            finished += 1
            if finished % 50 == 0:
                print(f"  {finished} {future.result()}", flush=True)
            else:
                future.result()
    with open(OUT, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["symbol", "first", "last", "days"])
        for symbol in symbols:
            row = (PARTS / f"{symbol}.csv").read_text().strip().split(",")
            writer.writerow(row)
    print(f"done: {len(symbols)}", flush=True)


if __name__ == "__main__":
    main()
