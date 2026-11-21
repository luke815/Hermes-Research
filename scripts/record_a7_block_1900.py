"""Record the 19:00 reading of the two things that block A7.

A7(1) waits on one close in data/panel_xs_laevitas. The close is copied
from the vendor price field, and on 2026-01-13 that field itself jumps
from 5.798e-06 to 0.00573127 while the index beside it stays near
0.00573. The panel copied a print the vendor file already has, so a
correction of the panel would be overwritten by the next rebuild from
the same file. A research run does not rewrite the panel and does not
pull. A7(3) waits on derivs_summary for five alts, which the
market_backfill daemon owns and which is not on disk. This reads both
and writes them through write_result, then appends the block note.
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs_laevitas", "binance_1000PEPEUSDT.csv")
SOURCE = os.path.join(ROOT, "data", "laevitas", "perpetuals", "BINANCE_1000PEPEUSDT.json")
MARKET = os.path.join(ROOT, "data", "laevitas", "market")
HEARTBEAT = os.path.join(ROOT, "ops", "market_backfill_heartbeat")
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
DATES = ("2026-01-12", "2026-01-13", "2026-01-14")
ALTS = ("ADA", "SOL", "LINK", "XRP", "AVAX")
JUMP = 50


def closes():
    lines = open(PANEL).read().splitlines()
    header = lines[0].split(",")
    close_at = header.index("close")
    found = {}
    for line in lines[1:]:
        row = line.split(",")
        if row[0] in DATES:
            found[row[0]] = float(row[close_at])
    return found


def source_days():
    """Vendor price beside index for the three days around the bad print."""
    body = json.loads(open(SOURCE).read())
    found = {}
    for item in body.get("items", []):
        day = datetime.fromtimestamp(
            item["date"] / 1000, timezone.utc).strftime("%Y-%m-%d")
        if day in DATES:
            found[day] = {"price": item.get("price"), "index": item.get("index")}
    return found


def ratio_jumps():
    """Days whose price/index ratio jumps by JUMP against the day before."""
    body = json.loads(open(SOURCE).read())
    rows = []
    for item in body.get("items", []):
        price, index = item.get("price"), item.get("index")
        if not price or not index:
            continue
        day = datetime.fromtimestamp(
            item["date"] / 1000, timezone.utc).strftime("%Y-%m-%d")
        rows.append((day, price / index))
    rows.sort()
    jumps = []
    for (day, ratio), (prev_day, prev) in zip(rows[1:], rows):
        if prev and (ratio / prev >= JUMP or prev / ratio >= JUMP):
            jumps.append({"date": day, "ratio": ratio, "prior_ratio": prev})
    return jumps


def price_jumps():
    """Days the vendor price field itself jumps by JUMP, index unchanged."""
    body = json.loads(open(SOURCE).read())
    rows = []
    for item in body.get("items", []):
        price, index = item.get("price"), item.get("index")
        if not price or not index:
            continue
        day = datetime.fromtimestamp(
            item["date"] / 1000, timezone.utc).strftime("%Y-%m-%d")
        rows.append((day, price, index))
    rows.sort()
    jumps = []
    for (day, price, index), (prev_day, prev_price, prev_index) in zip(rows[1:], rows):
        price_moved = prev_price and (
            price / prev_price >= JUMP or prev_price / price >= JUMP)
        index_held = prev_index and (1 / JUMP) < (index / prev_index) < JUMP
        if price_moved and index_held:
            jumps.append({
                "date": day, "price": price, "prior_price": prev_price,
                "index": index, "prior_index": prev_index})
    return jumps


def derivs_currencies():
    found = set()
    for name in os.listdir(MARKET):
        if name.startswith("derivs_summary_"):
            found.add(name.split("_")[2])
    return sorted(found)


def heartbeat():
    try:
        return json.loads(open(HEARTBEAT).read())
    except (OSError, json.JSONDecodeError):
        return {}


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    found = closes()
    bad = found.get("2026-01-13")
    still_bad = (
        bad is not None and bad > 0.001
        and found.get("2026-01-12", 1) < 0.0001
        and found.get("2026-01-14", 1) < 0.0001)
    vendor = source_days()
    day = vendor.get("2026-01-13", {})
    price, index = day.get("price"), day.get("index")
    ratio = (price / index) if price and index else None
    jumps = ratio_jumps()
    field_jumps = price_jumps()
    currencies = derivs_currencies()
    missing = [name for name in ALTS if name not in currencies]
    beat = heartbeat()
    payload = {
        "item": "A7",
        "today": today,
        "read_at": stamp,
        "slot": "19:00",
        "close_file": "data/panel_xs_laevitas/binance_1000PEPEUSDT.csv",
        "close_mtime": datetime.fromtimestamp(
            os.stat(PANEL).st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "closes": found,
        "still_bad": still_bad,
        "vendor_by_day": vendor,
        "vendor_price_over_index": ratio,
        "ratio_jumps_over_50": jumps,
        "ratio_jump_count": len(jumps),
        "vendor_price_field_jumps": field_jumps,
        "vendor_price_field_jump_count": len(field_jumps),
        "panel_matches_vendor_price": price == bad,
        "derivs_currencies": currencies,
        "alts_missing": missing,
        "market_backfill_remaining": beat.get("remaining"),
        "market_backfill_cycles": beat.get("cycles"),
        "market_backfill_phase": beat.get("phase"),
    }
    path = write_result("a7_block_1900", payload, inputs=[
        "data/panel_xs_laevitas/binance_1000PEPEUSDT.csv",
        "data/laevitas/perpetuals/BINANCE_1000PEPEUSDT.json",
        "data/laevitas/market"])
    print(path)
    print(json.dumps({k: payload[k] for k in (
        "still_bad", "panel_matches_vendor_price",
        "vendor_price_field_jump_count", "alts_missing",
        "market_backfill_remaining")}, default=str))
    if not still_bad or missing != list(ALTS):
        raise SystemExit("the block changed; not marking blocked")
    text = open(BACKLOG).read()
    marker = f"Rechecked {today} 19:00 UTC: results/{today}_a7_block_1900.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- A7. "))
    anchor = "The pre-registration is commit 2d78832."
    if line.count(anchor) != 1:
        raise SystemExit(f"anchor count {line.count(anchor)}")
    first = field_jumps[0] if field_jumps else {}
    note = (
        f"Rechecked {today} 19:00 UTC: results/{today}_a7_block_1900.json "
        f"shows the close on 2026-01-13 is {found['2026-01-13']} against "
        f"{found['2026-01-12']} on 2026-01-12 and {found['2026-01-14']} on "
        f"2026-01-14, file mtime {payload['close_mtime']}. The panel close "
        f"equals the vendor price field that day ({price}), and the vendor "
        f"price field itself jumps on {len(field_jumps)} days while the "
        f"index beside it does not, the first on {first.get('date')} from "
        f"{first.get('prior_price')} to {first.get('price')} against an "
        f"index of {first.get('index')}. Correcting the panel would be "
        f"overwritten by the next rebuild from the same file. "
        f"derivs_summary covers {', '.join(currencies)} and not "
        f"{', '.join(missing)}. market_backfill reports remaining "
        f"{payload['market_backfill_remaining']} at cycle "
        f"{payload['market_backfill_cycles']}, phase "
        f"{payload['market_backfill_phase']}. A7 stays blocked. Unblocks "
        f"when the vendor price field is corrected and the panel rebuilt, "
        f"and derivs_summary has a file for ADA, SOL, LINK, XRP and AVAX. "
        f"A research run does not rewrite the panel and does not pull. ")
    updated = line.replace(anchor, note + anchor, 1)
    open(BACKLOG, "w").write(text.replace(line, updated, 1))
    print("noted")


if __name__ == "__main__":
    main()
