"""D1 slice: open interest and long/short for the 16 long stopped names.

The metrics archive is one zip per day. This slice takes the stopped Binance
USDT perps whose listing has more than 250 daily files. Each symbol is written
to data/binance_metrics/ as soon as it is done, and a symbol whose saved dates
already equal the dates inside its archive files is skipped.
"""

import csv
import hashlib
import io
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester")
LISTING = ROOT / "data" / "binance_metrics_listing.csv"
OUT = ROOT / "data" / "binance_metrics"
BUCKET = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
MIN_ZIPS = 250
COLUMNS = [
    "date", "oi_contracts", "oi_usd", "count_toptrader_ls", "sum_toptrader_ls",
    "count_ls", "taker_ls", "observations", "undated_files",
]


def keys(prefix: str) -> list[str]:
    found: list[str] = []
    marker = ""
    pages = 0
    while True:
        query = "prefix=" + urllib.parse.quote(prefix, safe="/") + "&max-keys=1000"
        if marker:
            query += "&marker=" + urllib.parse.quote(marker, safe="")
        page_xml = fetch(f"{BUCKET}?{query}")
        root = ET.fromstring(page_xml)
        page = [k.text or "" for k in root.findall("s3:Contents/s3:Key", NS)]
        found.extend(k for k in page if k.endswith(".zip"))
        pages += 1
        if pages > 8:
            raise SystemExit(f"listing did not end under {prefix}")
        if root.findtext("s3:IsTruncated", default="false", namespaces=NS) != "true":
            return sorted(found)
        marker = root.findtext("s3:NextMarker", default="", namespaces=NS) or (
            page[-1] if page else "")
        if not marker:
            raise SystemExit(f"truncated page without a marker under {prefix}")
    return sorted(found)


def fetch(url: str) -> bytes:
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001
            if attempt == 3:
                raise
            print(f"  retry {url.rsplit('/', 1)[-1]}: {exc}", flush=True)
            time.sleep(2 * (attempt + 1))
    raise SystemExit("unreachable")


def read_zip(name: str) -> list[str]:
    blob = fetch(f"{BUCKET}/{name}")
    checksum = fetch(f"{BUCKET}/{name}.CHECKSUM").decode().split()[0]
    if hashlib.sha256(blob).hexdigest() != checksum:
        raise SystemExit(f"checksum failed for {name}")
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        return zf.read(zf.namelist()[0]).decode().strip().splitlines()


def read_all(names: list[str]) -> list[list[str]]:
    with ThreadPoolExecutor(max_workers=12) as pool:
        return list(pool.map(read_zip, names))


def file_date(name: str) -> str:
    stem = name.rsplit("-metrics-", 1)[-1][:-4]
    if len(stem) == 10 and stem[4] == "-" and stem[7] == "-":
        return stem
    return ""


def one(symbol: str) -> str:
    dest = OUT / f"{symbol}.csv"
    if dest.exists():
        saved = list(csv.DictReader(dest.open()))
        if saved and saved[-1]["date"] >= "2020-01-01":
            print(f"{symbol}: file present, {len(saved)} days, skipped", flush=True)
            return "saved"
    listed = keys(f"data/futures/um/daily/metrics/{symbol}/")
    undated = sum(1 for name in listed if not file_date(name))
    print(f"{symbol}: {len(listed)} files, {undated} undated", flush=True)
    if not listed:
        print(f"{symbol}: no files in the archive", flush=True)
        return "absent"
    by_day: dict[str, tuple[int, list[str]]] = {}
    counts: dict[str, int] = {}
    for batch_start in range(0, len(listed), 300):
        batch = listed[batch_start:batch_start + 300]
        for lines in read_all(batch):
            for line in lines:
                if line.startswith("create_time"):
                    continue
                parts = line.split(",")
                when = datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S").replace(
                    tzinfo=timezone.utc)
                day = when.date().isoformat()
                counts[day] = counts.get(day, 0) + 1
                stamp = int(when.timestamp())
                if day not in by_day or stamp >= by_day[day][0]:
                    by_day[day] = (stamp, parts)
        print(f"{symbol}: {min(batch_start + 300, len(listed))}/{len(listed)} files, "
              f"{len(by_day)} days", flush=True)
    if dest.exists():
        saved = {row["date"] for row in csv.DictReader(dest.open())}
        if saved == set(by_day):
            print(f"{symbol}: already saved, {len(saved)} days", flush=True)
            return "saved"
    rows = []
    for day in sorted(by_day):
        parts = by_day[day][1]
        rows.append({
            "date": day,
            "oi_contracts": parts[2],
            "oi_usd": parts[3],
            "count_toptrader_ls": parts[4],
            "sum_toptrader_ls": parts[5],
            "count_ls": parts[6],
            "taker_ls": parts[7],
            "observations": counts[day],
            "undated_files": undated,
        })
    with dest.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{symbol}: saved {len(rows)} days from {len(listed)} files, "
          f"{rows[0]['date']} -> {rows[-1]['date']}, undated {undated}", flush=True)
    return "saved"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    listed = list(csv.DictReader(LISTING.open()))
    chosen = sorted(row["symbol"] for row in listed if int(row["zips"]) > MIN_ZIPS)
    pending = []
    for symbol in chosen:
        dest = OUT / f"{symbol}.csv"
        if dest.exists():
            print(f"{symbol}: file present, rechecking against the archive", flush=True)
        pending.append(symbol)
    print(f"{len(chosen)} names above {MIN_ZIPS} files", flush=True)
    done = []
    for symbol in pending:
        done.append(one(symbol))
    print(f"done {len(done)}: {done.count('saved')} saved, {done.count('absent')} absent",
          flush=True)


if __name__ == "__main__":
    main()
