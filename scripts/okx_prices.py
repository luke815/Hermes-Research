"""Daily prices for the stopped OKX USDT perps, through 2023-12-31.

The archive publishes one all-swap candlestick file per day, about 7 MB, and
the index holds 1,888 days, which does not fit in one run. This slice keeps
the days from 2021-09-01 through 2023-12-31 and only the rows of the symbols
marked stopped in data/okx_span.csv. One day is written to
data/okx_price_parts/ as soon as it is parsed, and its rows are appended to
data/okx_prices/<SYMBOL>.csv in the same step, so a killed run resumes from
the days already saved. A part that does not end with the OK marker is
incomplete and is re-read.
"""

import csv
import io
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester/data")
INDEX = ROOT / "okx_index.csv"
SPAN = ROOT / "okx_span.csv"
PARTS = ROOT / "okx_price_parts"
OUT = ROOT / "okx_prices"
START = "2021-09-01"
END = "2023-12-31"
COLUMNS = ["date", "open", "high", "low", "close", "vol", "vol_ccy", "vol_quote", "open_time", "bars"]
HEADER = b"instrument_name,open,high,low,close,vol,vol_ccy,vol_quote,open_time,confirm"


def stopped_symbols() -> set[str]:
    with open(SPAN) as handle:
        rows = [row for row in csv.DictReader(handle) if row["stopped"] == "1"]
    return {row["symbol"] for row in rows}


def window() -> list[tuple[str, str]]:
    with open(INDEX) as handle:
        days = [(day, url) for day, url in csv.reader(handle) if START <= day <= END]
    if not days:
        raise RuntimeError("no index days in the window")
    if days[0][0] != START or days[-1][0] != END:
        raise RuntimeError(f"window bounds {days[0][0]} {days[-1][0]}")
    return days


def fetch(url: str) -> bytes:
    last = None
    for attempt in range(4):
        request = urllib.request.Request(url, headers={"User-Agent": "regime-tester"})
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"fetch failed: {url} {last}")


def number(value: str) -> float:
    if value in ("", "None"):
        return 0.0
    return float(value)


def daily_of(url: str, keep: set[str]) -> dict[str, list[str]]:
    """One daily candle per stopped symbol from the day's minute bars.

    The archive file holds 1,440 one-minute bars per instrument, not one row.
    The daily candle is the first bar's open, the day's high and low, the last
    bar's close, and the summed volumes. Bars are ordered by open time, not by
    file order, because a file is not guaranteed to be sorted.
    """
    bars: dict[str, list[tuple[int, list[str]]]] = {}
    with zipfile.ZipFile(io.BytesIO(fetch(url))) as archive:
        members = archive.namelist()
        if len(members) != 1:
            raise RuntimeError(f"expected one member, got {members[:3]}")
        with archive.open(members[0]) as handle:
            header = handle.readline().rstrip(b"\r\n")
            if header != HEADER:
                raise RuntimeError(f"unexpected header: {header[:80]!r}")
            for line in handle:
                symbol, _, rest = line.partition(b",")
                name = symbol.decode()
                if not name.endswith("-USDT-SWAP"):
                    continue
                base = name[: -len("-USDT-SWAP")]
                if base not in keep:
                    continue
                fields = rest.rstrip(b"\r\n").decode().split(",")
                if len(fields) != 9:
                    raise RuntimeError(f"short row: {name} {fields}")
                bars.setdefault(base, []).append((int(fields[7]), fields))
    candles = {}
    for base, series in bars.items():
        series.sort()
        opens = [row[1] for row in series]
        candles[base] = [
            opens[0][0],
            max(row[1] for row in opens),
            min(row[2] for row in opens),
            opens[-1][3],
            str(sum(number(row[4]) for row in opens)),
            str(sum(number(row[5]) for row in opens)),
            str(sum(number(row[6]) for row in opens)),
            opens[0][7],
            str(len(series)),
        ]
    return candles


def one(day: str, url: str, keep: set[str]) -> int:
    target = PARTS / f"{day}.txt"
    if target.exists() and target.read_text().endswith("\nOK\n"):
        return -1
    found = daily_of(url, keep)
    counts: dict[str, int] = {}
    for base, fields in found.items():
        path = OUT / f"{base}.csv"
        new = not path.exists()
        with open(path, "a") as handle:
            if new:
                handle.write(",".join(COLUMNS) + "\n")
            handle.write(",".join([day] + fields) + "\n")
        counts[base] = counts.get(base, 0) + 1
    if len(counts) != len(found):
        raise RuntimeError(f"duplicate symbol rows on {day}")
    target.write_text("".join(f"{base}\n" for base in sorted(counts)) + "OK\n")
    return len(found)


def main() -> None:
    PARTS.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    keep = stopped_symbols()
    days = window()
    pending = [(day, url) for day, url in days if not (PARTS / f"{day}.txt").exists()]
    print(f"stopped={len(keep)} days={len(days)} pending={len(pending)}", flush=True)
    failed = []
    finished = 0
    rows = 0
    with ThreadPoolExecutor(max_workers=6) as pool:
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
            if finished % 25 == 0:
                print(f"  {finished} {day} rows={rows}", flush=True)
    print(f"done: finished={finished} rows={rows} failed={len(failed)}", flush=True)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
