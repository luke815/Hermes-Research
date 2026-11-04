"""Confirm saved metrics dates equal the dates inside the archive files.

Checks the two names whose file count differs from their day count, plus one
other name, by reading every zip again. Prints the comparison and exits
non-zero if a saved file is missing a day the archive contains.
"""

import csv
import io
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

BUCKET = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
ROOT = "/opt/data/workspace/regime-tester/data/binance_metrics"


def keys(prefix: str) -> list[str]:
    found: list[str] = []
    marker = ""
    while True:
        query = "prefix=" + urllib.parse.quote(prefix, safe="/") + "&max-keys=1000"
        if marker:
            query += "&marker=" + urllib.parse.quote(marker, safe="")
        with urllib.request.urlopen(f"{BUCKET}?{query}", timeout=90) as resp:
            root = ET.fromstring(resp.read())
        page = [k.text or "" for k in root.findall("s3:Contents/s3:Key", NS)]
        found.extend(k for k in page if k.endswith(".zip"))
        if root.findtext("s3:IsTruncated", default="false", namespaces=NS) != "true":
            return found
        marker = root.findtext("s3:NextMarker", default="", namespaces=NS) or page[-1]


def days_of(name: str) -> set[str]:
    import time
    last = None
    for attempt in range(4):
        try:
            blob = urllib.request.urlopen(f"{BUCKET}/{name}", timeout=90).read()
            break
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2 * (attempt + 1))
    else:
        raise last
    lines = zipfile.ZipFile(io.BytesIO(blob)).read(
        zipfile.ZipFile(io.BytesIO(blob)).namelist()[0]).decode().strip().splitlines()
    return {datetime.strptime(line.split(",")[0], "%Y-%m-%d %H:%M:%S").date().isoformat()
            for line in lines[1:]}


def check(symbol: str) -> bool:
    names = keys(f"data/futures/um/daily/metrics/{symbol}/")
    with ThreadPoolExecutor(max_workers=16) as pool:
        sets = list(pool.map(days_of, names))
    archive = set().union(*sets)
    saved = {row["date"] for row in csv.DictReader(open(f"{ROOT}/{symbol}.csv"))}
    print(f"{symbol}: zips={len(names)} archive_days={len(archive)} "
          f"saved_days={len(saved)} equal={archive == saved} "
          f"missing={len(archive - saved)} extra={len(saved - archive)}")
    return archive == saved


def main() -> None:
    symbols = sys.argv[1:]
    ok = all(check(symbol) for symbol in symbols)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
