"""D1 slice: daily funding for the 31 Binance USDT perps that stopped before
2026-10-19.

Reads the monthly fundingRate archive. One row per UTC day, taken from the
last settlement of that day, with the count of settlements kept beside it.
Each symbol is written to data/binance_funding/ as soon as it is done, and a
symbol whose saved file already covers every month in its listing is skipped.
"""

import csv
import hashlib
import io
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester")
SPAN = ROOT / "data" / "binance_span.csv"
OUT = ROOT / "data" / "binance_funding"
BUCKET = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
CUTOFF = date(2026, 10, 19)
COLUMNS = ["date", "funding_rate", "settlements"]


def keys(prefix: str) -> list[str]:
    found: list[str] = []
    marker = ""
    pages = 0
    while True:
        query = "prefix=" + urllib.parse.quote(prefix, safe="/") + "&max-keys=1000"
        if marker:
            query += "&marker=" + urllib.parse.quote(marker, safe="")
        with urllib.request.urlopen(f"{BUCKET}?{query}", timeout=90) as resp:
            root = ET.fromstring(resp.read())
        page = [k.text or "" for k in root.findall("s3:Contents/s3:Key", NS)]
        found.extend(k for k in page if k.endswith(".zip"))
        pages += 1
        if pages > 40:
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


def one(symbol: str) -> str:
    dest = OUT / f"{symbol}.csv"
    listed = keys(f"data/futures/um/monthly/fundingRate/{symbol}/")
    months = {name.rsplit("-fundingRate-", 1)[-1][:7] for name in listed}
    if dest.exists() and months:
        saved = list(csv.DictReader(dest.open()))
        if saved and {r["date"][:7] for r in saved} == months:
            print(f"{symbol}: already saved, {len(saved)} days", flush=True)
            return "saved"
    if not listed:
        print(f"{symbol}: no files in the archive", flush=True)
        return "absent"
    by_day: dict[str, tuple[int, str]] = {}
    counts: dict[str, int] = {}
    for name in listed:
        for line in read_zip(name):
            if line.startswith("calc_time"):
                continue
            stamp, _interval, rate = line.split(",")[:3]
            when = datetime.fromtimestamp(int(stamp) / 1000, timezone.utc)
            day = when.date().isoformat()
            counts[day] = counts.get(day, 0) + 1
            if day not in by_day or int(stamp) > by_day[day][0]:
                by_day[day] = (int(stamp), rate)
    rows = [{"date": day, "funding_rate": by_day[day][1], "settlements": counts[day]}
            for day in sorted(by_day)]
    covered = {r["date"][:7] for r in rows}
    if covered != months:
        raise SystemExit(f"{symbol}: parsed months {sorted(covered)} != listing {sorted(months)}")
    with dest.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{symbol}: saved {len(rows)} days from {len(listed)} months, "
          f"{rows[0]['date']} -> {rows[-1]['date']}", flush=True)
    return "saved"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    rows = list(csv.DictReader(SPAN.open()))
    stopped = [r["symbol"] for r in rows if date.fromisoformat(r["last"]) < CUTOFF]
    print(f"{len(stopped)} stopped names", flush=True)
    done = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(one, symbol) for symbol in stopped]
        for future in as_completed(futures):
            done.append(future.result())
    print(f"done {len(done)}: {done.count('saved')} saved, {done.count('absent')} absent",
          flush=True)


if __name__ == "__main__":
    main()
