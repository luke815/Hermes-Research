"""D1 slice: daily klines for the 31 Binance USDT perps that stopped before 2026-10-19.

Uses the monthly archives and only the daily files for the final partial month.
Each symbol is written to data/binance_prices/ as soon as it is done, and a
symbol whose saved file already matches the listing is skipped.
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
OUT = ROOT / "data" / "binance_prices"
BUCKET = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
CUTOFF = date(2026, 10, 19)
COLUMNS = ["date", "open", "high", "low", "close", "volume", "trades"]


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
        marker = root.findtext("s3:NextMarker", default="", namespaces=NS) or (
            page[-1] if page else "")
        if not marker:
            raise SystemExit(f"truncated page without a marker under {prefix}")


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


def rows_of(name: str) -> list[dict]:
    blob = fetch(f"{BUCKET}/{name}")
    checksum = fetch(f"{BUCKET}/{name}.CHECKSUM").decode().split()[0]
    if hashlib.sha256(blob).hexdigest() != checksum:
        raise SystemExit(f"checksum failed for {name}")
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        raw = zf.read(zf.namelist()[0]).decode().strip().splitlines()
    rows = []
    for line in raw:
        if line.startswith("open_time"):
            continue
        c = line.split(",")
        rows.append({
            "date": datetime.fromtimestamp(int(c[0]) / 1000, timezone.utc).date().isoformat(),
            "open": c[1], "high": c[2], "low": c[3], "close": c[4],
            "volume": c[5], "trades": c[8],
        })
    return rows


def one(symbol: str, listed_last: str, listed_days: int) -> None:
    dest = OUT / f"{symbol}.csv"
    if dest.exists():
        saved = list(csv.DictReader(dest.open()))
        if saved and len(saved) == listed_days and saved[-1]["date"] == listed_last:
            print(f"{symbol}: already saved, {len(saved)} rows", flush=True)
            return
    monthly = sorted(keys(f"data/futures/um/monthly/klines/{symbol}/1d/"))
    daily = sorted(keys(f"data/futures/um/daily/klines/{symbol}/1d/"))
    by_month: dict[str, list[dict]] = {}
    for name in monthly:
        month = name.rsplit("-1d-", 1)[-1][:7]
        by_month.setdefault(month, []).extend(rows_of(name))
    listed = {name.rsplit("-1d-", 1)[-1][:10] for name in daily}
    extra = sorted({r["date"] for rows in by_month.values() for r in rows} - listed)
    for month in by_month:
        by_month[month] = [r for r in by_month[month] if r["date"] in listed]
    filled = []
    for name in daily:
        day = name.rsplit("-1d-", 1)[-1][:10]
        month = day[:7]
        have = {r["date"] for r in by_month.get(month, [])}
        if day not in have:
            by_month.setdefault(month, []).extend(rows_of(name))
            filled.append(day)
    out_rows = [r for month in sorted(by_month) for r in by_month[month]]
    out_rows.sort(key=lambda r: r["date"])
    seen = [r["date"] for r in out_rows]
    if len(seen) != len(set(seen)):
        raise SystemExit(f"{symbol}: duplicate dates")
    if len(out_rows) != listed_days or out_rows[-1]["date"] != listed_last:
        raise SystemExit(f"{symbol}: parsed {len(out_rows)} ending {out_rows[-1]['date']} "
                         f"!= span {listed_days} ending {listed_last}")
    with dest.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, COLUMNS)
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"{symbol}: saved {len(out_rows)} rows from {len(monthly)} monthly"
          f"{f', filled {len(filled)} gap days' if filled else ''}"
          f"{f', dropped {len(extra)} days absent from the daily listing' if extra else ''}, "
          f"{out_rows[0]['date']} -> {out_rows[-1]['date']}", flush=True)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    rows = list(csv.DictReader(SPAN.open()))
    stopped = [r for r in rows if date.fromisoformat(r["last"]) < CUTOFF]
    print(f"{len(stopped)} stopped names", flush=True)
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(one, r["symbol"], r["last"], int(r["days"])) for r in stopped]
        for future in as_completed(futures):
            future.result()
    print("done", flush=True)


if __name__ == "__main__":
    main()
