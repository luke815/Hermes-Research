"""First and last day per OKX USDT perpetual, from the public candlestick archive.

OKX publishes no bucket of symbol folders. The market-data-history index lists
one all-swap candlestick file per day, and each file names every swap that
traded that day. This slice keeps the names ending in -USDT-SWAP and records
the first and last day each appears. One day is written to data/okx_span_parts/
as soon as it is parsed, so a killed run resumes from the days already saved.
A part that does not end with the OK marker is incomplete and is re-read.
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
PARTS = ROOT / "okx_span_parts"
OUT = ROOT / "okx_span.csv"
INDEX = ROOT / "okx_index.csv"
START = datetime(2021, 9, 1, tzinfo=timezone.utc)
WINDOW_DAYS = 10
STOP_DAYS = 14
SUFFIX = "-USDT-SWAP"
INDEX_URL = "https://www.okx.com/api/v5/public/market-data-history"


def get(url: str) -> bytes:
    last = None
    for attempt in range(4):
        request = urllib.request.Request(url, headers={"User-Agent": "regime-tester"})
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"fetch failed: {url} {last}")


def ms(moment: datetime) -> str:
    return str(int(moment.timestamp() * 1000))


def index_window(begin: datetime, end: datetime) -> list[tuple[str, str]]:
    url = (f"{INDEX_URL}?module=2&instType=SWAP&instFamilyList=ANY"
           f"&dateAggrType=daily&begin={ms(begin)}&end={ms(end)}")
    payload = json.loads(get(url))
    if payload.get("code") != "0":
        raise RuntimeError(f"index {payload.get('code')} {payload.get('msg')}")
    found = []
    for group in payload.get("data") or []:
        for detail in group.get("details") or []:
            for item in detail.get("groupDetails") or []:
                name = item.get("filename") or ""
                if not name.startswith("allswap-candlesticks-"):
                    continue
                day = name[len("allswap-candlesticks-"):-len(".zip")]
                found.append((day, item["url"]))
    return sorted(set(found))


def index_all(today: datetime) -> list[tuple[str, str]]:
    found = {}
    cursor = START
    while cursor.date() <= today.date():
        end = min(cursor + timedelta(days=WINDOW_DAYS - 1), today)
        for day, url in index_window(cursor, end):
            found[day] = url
        print(f"  index {cursor.date().isoformat()} files={len(found)}", flush=True)
        cursor = end + timedelta(days=1)
        time.sleep(0.2)
    return sorted(found.items())


def symbols_of(url: str) -> list[str]:
    blob = get(url)
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        members = archive.namelist()
        if len(members) != 1:
            raise RuntimeError(f"expected one member, got {members[:3]}")
        seen = set()
        with archive.open(members[0]) as handle:
            header = handle.readline()
            if not header.startswith(b"instrument_name,"):
                raise RuntimeError("missing header")
            for line in handle:
                name = line.split(b",", 1)[0].decode()
                if name.endswith(SUFFIX):
                    seen.add(name[: -len(SUFFIX)])
        if not seen:
            raise RuntimeError("no USDT swaps in file")
    return sorted(seen)


def one(day: str, url: str) -> str:
    target = PARTS / f"{day}.txt"
    if target.exists() and target.read_text().endswith("\nOK\n"):
        return day
    names = symbols_of(url)
    target.write_text("\n".join(names) + "\nOK\n")
    return day


def main() -> None:
    PARTS.mkdir(exist_ok=True)
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    print(f"today={today.date().isoformat()}", flush=True)
    listed = index_all(today - timedelta(days=2))
    INDEX.write_text("".join(f"{day},{url}\n" for day, url in listed))
    pending = [(d, u) for d, u in listed if not (PARTS / f"{d}.txt").exists()]
    print(f"{len(listed)} days listed, {len(listed) - len(pending)} done, {len(pending)} left", flush=True)
    failed = []
    finished = 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(one, day, url): day for day, url in pending}
        for future in as_completed(futures):
            day = futures[future]
            try:
                future.result()
            except Exception as exc:
                failed.append((day, str(exc)))
                print(f"  FAIL {day} {exc}", flush=True)
                continue
            finished += 1
            if finished % 50 == 0:
                print(f"  {finished} {day}", flush=True)
    spans: dict[str, list] = {}
    written = 0
    for day, _url in listed:
        part = PARTS / f"{day}.txt"
        if not part.exists() or not part.read_text().endswith("\nOK\n"):
            continue
        written += 1
        for symbol in part.read_text().splitlines()[:-1]:
            span = spans.setdefault(symbol, [day, day, 0])
            span[0] = min(span[0], day)
            span[1] = max(span[1], day)
            span[2] += 1
    rows = []
    for symbol in sorted(spans):
        first, last, days = spans[symbol]
        last_date = datetime.strptime(last, "%Y-%m-%d").date()
        stopped = (today.date() - last_date).days > STOP_DAYS
        rows.append([symbol, first, last, days, "1" if stopped else "0"])
    with open(OUT, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["symbol", "first", "last", "days", "stopped"])
        writer.writerows(rows)
    print(
        f"done: listed={len(listed)} written={written} failed={len(failed)} "
        f"symbols={len(rows)} stopped={sum(r[-1] == '1' for r in rows)} "
        f"today={today.date().isoformat()}",
        flush=True,
    )
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
