"""Daily funding for the stopped OKX USDT perps, from the public funding archive.

The funding index is a separate module from the candlestick index, so this
slice builds its own index and writes it to data/okx_funding_index.csv. One
day is written to data/okx_funding_parts/ as soon as it is parsed, and its row
is appended to data/okx_funding/<SYMBOL>.csv in the same step, so a killed run
resumes from the days already saved. A part that does not end with the OK
marker is incomplete and is re-read.
"""

import csv
import io
import json
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester/data")
SPAN = ROOT / "okx_span.csv"
INDEX = ROOT / "okx_funding_index.csv"
PARTS = ROOT / "okx_funding_parts"
OUT = ROOT / "okx_funding"
START = datetime(2021, 9, 1, tzinfo=timezone.utc)
WINDOW_DAYS = 10
INDEX_URL = "https://www.okx.com/api/v5/public/market-data-history"
SUFFIX = "-USDT-SWAP"
HEADER = b"instrument_name,funding_rate,funding_time"
COLUMNS = ["date", "funding_rate", "funding_time", "settlements", "funding_mean", "blank_settlements"]


def stopped_symbols() -> set[str]:
    with open(SPAN) as handle:
        rows = [row for row in csv.DictReader(handle) if row["stopped"] == "1"]
    return {row["symbol"] for row in rows}


def get(url: str) -> bytes:
    last = None
    for attempt in range(4):
        request = urllib.request.Request(url, headers={"User-Agent": "regime-tester"})
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"fetch failed: {url} {last}")


def index_window(begin: datetime, end: datetime) -> list[tuple[str, str]]:
    url = (f"{INDEX_URL}?module=3&instType=SWAP&instFamilyList=ANY"
           f"&dateAggrType=daily&begin={int(begin.timestamp() * 1000)}"
           f"&end={int(end.timestamp() * 1000)}")
    payload = json.loads(get(url))
    if payload.get("code") != "0":
        raise RuntimeError(f"index {payload.get('code')} {payload.get('msg')}")
    found = []
    for group in payload.get("data") or []:
        for detail in group.get("details") or []:
            for item in detail.get("groupDetails") or []:
                name = item.get("filename") or ""
                if not name.startswith("allswap-fundingrates-"):
                    continue
                day = name[len("allswap-fundingrates-"):-len(".zip")]
                found.append((day, item["url"]))
    return sorted(set(found))


def index_all(today: datetime) -> list[tuple[str, str]]:
    if INDEX.exists() and INDEX.stat().st_size > 0:
        with open(INDEX) as handle:
            saved = [(day, url) for day, url in csv.reader(handle)]
        if saved and saved[-1][0] >= (today - timedelta(days=2)).date().isoformat():
            print(f"  index reused, {len(saved)} days through {saved[-1][0]}", flush=True)
            return saved
    found = {}
    cursor = START
    while cursor.date() <= today.date():
        end = min(cursor + timedelta(days=WINDOW_DAYS - 1), today)
        for day, url in index_window(cursor, end):
            found[day] = url
        print(f"  index {cursor.date().isoformat()} files={len(found)}", flush=True)
        cursor = end + timedelta(days=1)
        time.sleep(0.2)
    listed = sorted(found.items())
    INDEX.write_text("".join(f"{day},{url}\n" for day, url in listed))
    return listed


def daily_of(url: str, keep: set[str]) -> dict[str, list[str]]:
    """Last settlement of the UTC day per stopped symbol, plus the day mean."""
    rows: dict[str, list[tuple[int, str]]] = {}
    with zipfile.ZipFile(io.BytesIO(get(url))) as archive:
        members = archive.namelist()
        if len(members) != 1:
            raise RuntimeError(f"expected one member, got {members[:3]}")
        with archive.open(members[0]) as handle:
            header = handle.readline().strip()
            if header != HEADER:
                raise RuntimeError(f"unexpected header: {header[:80]!r}")
            for line in handle:
                symbol, _, rest = line.partition(b",")
                name = symbol.decode()
                if not name.endswith(SUFFIX):
                    continue
                base = name[: -len(SUFFIX)]
                if base not in keep:
                    continue
                rate, _, moment = rest.rstrip(b"\r\n").partition(b",")
                rows.setdefault(base, []).append((int(moment), rate.decode()))
    out = {}
    for base, series in rows.items():
        series.sort()
        numeric = [(moment, rate) for moment, rate in series if rate not in ("", "None")]
        # The archive publishes the literal string None for some settlements.
        # A day whose every settlement is None is kept and flagged, not dropped,
        # because the name did have a funding row that day.
        if not numeric:
            last_time, _ = series[-1]
            out[base] = ["", str(last_time), str(len(series)), "", "1"]
            continue
        rates = [float(rate) for _, rate in numeric]
        last_time, last_rate = numeric[-1]
        blank = len(series) - len(numeric)
        out[base] = [last_rate, str(last_time), str(len(series)), repr(sum(rates) / len(rates)), str(blank)]
    return out


def one(day: str, url: str, keep: set[str]) -> int:
    target = PARTS / f"{day}.txt"
    if target.exists() and target.read_text().endswith("OK\n"):
        return -1
    found = daily_of(url, keep)
    for base, fields in found.items():
        path = OUT / f"{base}.csv"
        new = not path.exists()
        with open(path, "a") as handle:
            if new:
                handle.write(",".join(COLUMNS) + "\n")
            handle.write(",".join([day] + fields) + "\n")
    target.write_text("".join(f"{base}\n" for base in sorted(found)) + "OK\n")
    return len(found)


def main() -> None:
    PARTS.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    print(f"today={today.date().isoformat()}", flush=True)
    keep = stopped_symbols()
    listed = index_all(today - timedelta(days=2))
    pending = [(day, url) for day, url in listed if not (PARTS / f"{day}.txt").exists()]
    print(f"stopped={len(keep)} days={len(listed)} pending={len(pending)}", flush=True)
    failed = []
    finished = 0
    rows = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(one, day, url, keep): day for day, url in pending}
        for future in as_completed(futures):
            day = futures[future]
            try:
                added = future.result()
            except Exception as exc:
                failed.append((day, str(exc)))
                print(f"  FAIL {day} {exc}", flush=True)
                continue
            finished += 1
            rows += max(added, 0)
            if finished % 100 == 0:
                print(f"  {finished} {day} rows={rows}", flush=True)
    print(f"done: finished={finished} rows={rows} failed={len(failed)}", flush=True)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
