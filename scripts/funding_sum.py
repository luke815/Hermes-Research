"""Daily funding as the sum of the day's settlements, for every venue.

The stores keep the last print of the day, or the mean, with a count beside
it. Multiplying the last print by the count is not the day's funding, and a
mean times a count that includes blank settlements is not either. This reads
the settlements themselves, pages back through the history, and sums the
numeric prints of each UTC day. A day whose every print is blank is absent,
not zero. Today's unfinished bar is not written.

One name per call, so a daemon can walk the list. The sum is written to
data/funding_sum/<exchange>_<symbol>.csv as it arrives, and a name whose file
already ends on the last closed day is skipped.
"""

import json
import os
import sys

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rate_budget  # noqa: E402
from regime_tester.panel_integrity import sum_funding, today_utc  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "funding_sum")


def _hours(prints, default):
    """Hours between consecutive settlements, from the prints themselves."""
    stamps = sorted({int(stamp) for stamp, _rate in prints})
    gaps = [b - a for a, b in zip(stamps, stamps[1:]) if b > a]
    if not gaps:
        return default
    hours = round(min(gaps) / 3_600_000)
    return hours if hours in (1, 2, 4, 8) else default


def binance_prints(symbol, pages=4):
    """Settlements for one Binance name, newest page first, paged by endTime.

    The endpoint returns 500 rows even when more are asked for, so the next
    page ends one millisecond before the oldest stamp already seen.
    """
    from urllib.parse import quote
    prints = []
    end = None
    for _page in range(pages):
        url = ("https://fapi.binance.com/fapi/v1/fundingRate?symbol="
               + quote(symbol, safe="") + "&limit=1000")
        if end is not None:
            url += f"&endTime={end}"
        rows = json.loads(rate_budget.get(url, timeout=30))
        if not rows:
            break
        batch = [(int(row["fundingTime"]), float(row["fundingRate"])) for row in rows]
        prints.extend(batch)
        oldest = min(stamp for stamp, _rate in batch)
        if end is not None and oldest >= end:
            break
        end = oldest - 1
        if len(rows) < 500:
            break
    return prints


def bybit_prints(symbol, pages=6):
    """Settlements for one Bybit name, paged by endTime. 200 rows a page."""
    from urllib.parse import quote
    prints = []
    end = None
    for _page in range(pages):
        url = ("https://api.bybit.com/v5/market/funding/history?category=linear&symbol="
               + quote(symbol, safe="") + "&limit=200")
        if end is not None:
            url += f"&endTime={end}"
        got = json.loads(rate_budget.get(url, timeout=30))
        rows = got.get("result", {}).get("list", [])
        if not rows:
            break
        batch = [(int(row["fundingRateTimestamp"]), float(row["fundingRate"])) for row in rows]
        prints.extend(batch)
        oldest = min(stamp for stamp, _rate in batch)
        if end is not None and oldest >= end:
            break
        end = oldest - 1
        if len(rows) < 200:
            break
    return prints


def okx_prints(symbol, pages=8):
    """Settlements for one OKX swap, paged by after. A blank rate is skipped.

    A blank settlement is not a zero rate, so it is left out of the sum and
    out of the count. A day whose every settlement is blank is then absent.
    """
    from urllib.parse import quote
    prints = []
    after = None
    for _page in range(pages):
        url = ("https://www.okx.com/api/v5/public/funding-rate-history?instId="
               + quote(symbol, safe="") + "&limit=100")
        if after is not None:
            url += f"&after={after}"
        got = json.loads(rate_budget.get(url, timeout=30))
        rows = got.get("data", [])
        if not rows:
            break
        batch = []
        for row in rows:
            rate = row.get("fundingRate")
            if rate in (None, "", "None"):
                continue
            batch.append((int(row["fundingTime"]), float(rate)))
        prints.extend(batch)
        oldest = min(int(row["fundingTime"]) for row in rows)
        if after is not None and oldest >= after:
            break
        after = oldest
        if len(rows) < 100:
            break
    return prints


FETCH = {"binance": binance_prints, "bybit": bybit_prints, "okx": okx_prints}


def daily_sum(exchange, symbol, today=None):
    """The day's funding sum and its interval, with today left out."""
    prints = FETCH[exchange](symbol)
    if not prints:
        return {}
    summed = sum_funding(prints, _hours(prints, default=8))
    cutoff = today if today is not None else today_utc()
    return {day: values for day, values in summed.items() if day < cutoff}


def write_sum(exchange, symbol, today=None):
    """Write one name's daily sum, skipping a file that already ends closed."""
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{exchange}_{symbol}.csv")
    cutoff = today if today is not None else today_utc()
    if os.path.exists(path) and os.path.getsize(path) > 40:
        with open(path) as handle:
            lines = handle.read().splitlines()
        if len(lines) > 1 and lines[-1].split(",")[0] >= _previous(cutoff):
            return path, 0
    summed = daily_sum(exchange, symbol, today=cutoff)
    rows = ["date,funding_rate,funding_count,funding_interval_hours"]
    for day in sorted(summed):
        values = summed[day]
        rows.append(f"{day},{values['funding_rate']},{values['funding_count']},"
                    f"{values['funding_interval_hours']}")
    tmp = path + ".tmp"
    with open(tmp, "w") as handle:
        handle.write("\n".join(rows) + "\n")
    os.replace(tmp, path)
    return path, len(summed)


def _previous(day):
    """The UTC date one day before day, so a closed file is recognizable."""
    from datetime import timedelta
    return (datetime.fromisoformat(day) - timedelta(days=1)).strftime("%Y-%m-%d")


def okx_archive_day(day, url, symbols):
    """The day's funding sum per symbol, from one archive zip.

    symbols is a set of base names (BTC, not BTC-USDT-SWAP). A blank rate is
    left out of the sum and the count, so a day of only blanks is absent. The
    sum is the numeric settlements added, which is not the last print times
    the count of rows.
    """
    import io
    import zipfile
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from http_get import fetch
    found: dict[str, list] = {}
    blob = fetch(url, timeout=120)
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        member = archive.namelist()[0]
        for line in archive.read(member).decode().splitlines():
            symbol, _, rest = line.partition(",")
            if not symbol.endswith("-USDT-SWAP"):
                continue
            base = symbol[: -len("-USDT-SWAP")]
            if base not in symbols:
                continue
            rate, _, moment = rest.rstrip().partition(",")
            if rate in ("", "None"):
                continue
            found.setdefault(base, []).append((int(moment), float(rate)))
    return {base: sum_funding(prints, _hours(prints, 8)).get(day)
            for base, prints in found.items()}


def _append_sum(exchange, symbol, day, values):
    """Append one closed day to a name's sum file, replacing that day if present."""
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{exchange}_{symbol}.csv")
    rows = {}
    if os.path.exists(path):
        for line in open(path).read().splitlines()[1:]:
            parts = line.split(",")
            if len(parts) >= 4:
                rows[parts[0]] = line
    rows[day] = (f"{day},{values['funding_rate']},{values['funding_count']},"
                 f"{values['funding_interval_hours']}")
    body = ["date,funding_rate,funding_count,funding_interval_hours"]
    body.extend(rows[d] for d in sorted(rows))
    tmp = path + ".tmp"
    with open(tmp, "w") as handle:
        handle.write("\n".join(body) + "\n")
    os.replace(tmp, path)
