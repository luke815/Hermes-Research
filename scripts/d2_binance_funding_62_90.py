"""D2 slice: daily funding for live Binance USDT perps with a 62 to 90 day span.

Cross-venue divergence needs each venue's own funding history. The panel files
hold only the last thousand settlements, so this reads the monthly fundingRate
archive instead. One row per UTC day, taken from the last settlement of that
day, with the count of settlements kept beside it. Each symbol is written to
data/binance_funding/ as soon as it is done, and a symbol whose saved file
already covers every month in its listing is skipped.

Bound: exchange binance, delisted 0, span from first_bar to last_bar of 62 to
90 days inclusive. 29 names. No other venue, no open interest, no return scored.
"""

import csv
import hashlib
import io
import sys
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from http_get import fetch  # noqa: E402

ROOT = Path("/opt/data/workspace/regime-tester")
UNIVERSE = ROOT / "data" / "universe.csv"
OUT = ROOT / "data" / "binance_funding"
BUCKET = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
MIN_SPAN_DAYS = 62
MAX_SPAN_DAYS = 90
COLUMNS = ["date", "funding_rate", "settlements"]


def keys(prefix: str) -> list[str]:
    found: list[str] = []
    marker = ""
    pages = 0
    while True:
        query = "prefix=" + urllib.parse.quote(prefix, safe="/") + "&max-keys=1000"
        if marker:
            query += "&marker=" + urllib.parse.quote(marker, safe="")
        root = ET.fromstring(fetch(f"{BUCKET}?{query}", timeout=90))
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


def read_zip(name: str) -> list[str]:
    path = urllib.parse.quote(name, safe="/")
    blob = fetch(f"{BUCKET}/{path}")
    checksum = fetch(f"{BUCKET}/{path}.CHECKSUM").decode().split()[0]
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


def targets() -> list[str]:
    rows = list(csv.DictReader(UNIVERSE.open()))
    out = []
    for row in rows:
        if row["exchange"] != "binance" or row["delisted"] != "0":
            continue
        first = date.fromisoformat(row["first_bar"])
        last = date.fromisoformat(row["last_bar"])
        span = (last - first).days + 1
        if MIN_SPAN_DAYS <= span <= MAX_SPAN_DAYS:
            out.append(row["symbol"])
    return out


def main() -> None:
    OUT.mkdir(exist_ok=True)
    symbols = targets()
    print(f"{len(symbols)} live names with a span of {MIN_SPAN_DAYS} to {MAX_SPAN_DAYS} days", flush=True)
    done = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(one, symbol) for symbol in symbols]
        for future in as_completed(futures):
            done.append(future.result())
    print(f"done {len(done)}: {done.count('saved')} saved, {done.count('absent')} absent",
          flush=True)


if __name__ == "__main__":
    main()
