"""Record the 11:00 reading of the two things that block A7.

A7(1) waits on one close in data/panel_xs_laevitas, which a research run does
not rewrite. A7(3) waits on derivs_summary for five alts, which the
market_backfill daemon owns and which is not on disk. This reads both and
writes them through write_result, then appends the block note to the A7 line.
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs_laevitas", "binance_1000PEPEUSDT.csv")
MARKET = os.path.join(ROOT, "data", "laevitas", "market")
HEARTBEAT = os.path.join(ROOT, "ops", "market_backfill_heartbeat")
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
DATES = ("2026-01-12", "2026-01-13", "2026-01-14")
ALTS = ("ADA", "SOL", "LINK", "XRP", "AVAX")


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
    currencies = derivs_currencies()
    missing = [name for name in ALTS if name not in currencies]
    beat = heartbeat()
    payload = {
        "item": "A7",
        "today": today,
        "read_at": stamp,
        "slot": "11:00",
        "close_file": "data/panel_xs_laevitas/binance_1000PEPEUSDT.csv",
        "close_mtime": datetime.fromtimestamp(
            os.stat(PANEL).st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "closes": found,
        "still_bad": still_bad,
        "derivs_currencies": currencies,
        "alts_missing": missing,
        "market_backfill_remaining": beat.get("remaining"),
        "market_backfill_cycles": beat.get("cycles"),
    }
    path = write_result("a7_block_1100", payload, inputs=[
        "data/panel_xs_laevitas/binance_1000PEPEUSDT.csv",
        "data/laevitas/market"])
    print(path)
    if not still_bad or missing != list(ALTS):
        raise SystemExit("the block changed; not marking blocked")
    text = open(BACKLOG).read()
    marker = f"Rechecked {today} 11:00 UTC: results/{today}_a7_block_1100.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- A7. "))
    anchor = "A research run does not rewrite the panel and does not pull."
    if line.count(anchor) != 1:
        raise SystemExit(f"anchor count {line.count(anchor)}")
    note = (
        f" Rechecked {today} 11:00 UTC: results/{today}_a7_block_1100.json "
        f"shows the close on 2026-01-13 is {found['2026-01-13']} against "
        f"{found['2026-01-12']} on 2026-01-12 and {found['2026-01-14']} on "
        f"2026-01-14, file mtime {payload['close_mtime']}. derivs_summary "
        f"covers {', '.join(currencies)} and not {', '.join(missing)}. "
        f"market_backfill reports remaining "
        f"{payload['market_backfill_remaining']} at cycle "
        f"{payload['market_backfill_cycles']}, so the walk is finished and "
        f"the vendor returned nothing for those five. A7 stays blocked. "
        f"Unblocks when that close is corrected in data/panel_xs_laevitas and "
        f"derivs_summary has a file for ADA, SOL, LINK, XRP and AVAX. A "
        f"research run does not rewrite the panel and does not pull.")
    updated = line.replace(anchor, anchor + note, 1)
    open(BACKLOG, "w").write(text.replace(line, updated, 1))
    print("noted")


if __name__ == "__main__":
    main()
