"""Record one recheck of the series that blocks Q4.

Q4 waits on oi_pc_ratio having a bar after 2025-06 for BTC and ETH. The
market_backfill daemon owns that pull, and a research run does not pull.
The slot is today's UTC hour, read from the clock. This counts the files
and reads the daemon's heartbeat, writes them through write_result, and
appends the block note.

Usage: python3 scripts/record_q4_reading.py
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKET = os.path.join(ROOT, "data", "laevitas", "market")
HEARTBEAT = os.path.join(ROOT, "ops", "market_backfill_heartbeat")
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
ASSETS = ("BTC", "ETH")
CUTOFF = "2025-06"
ANCHOR = "Unblocks when oi_pc_ratio has a bar after 2025-06 for BTC and ETH."


def series(asset):
    prefix = f"oi_pc_ratio_{asset}_"
    names = sorted(name for name in os.listdir(MARKET) if name.startswith(prefix))
    empty = 0
    last = None
    for name in names:
        path = os.path.join(MARKET, name)
        if os.path.getsize(path) == 0:
            empty += 1
            continue
        rows = json.load(open(path))
        items = rows.get("items") if isinstance(rows, dict) else rows
        if not items:
            empty += 1
            continue
        dates = []
        for row in items:
            if not isinstance(row, dict) or "date" not in row:
                continue
            stamp = row["date"]
            if isinstance(stamp, (int, float)):
                stamp = datetime.fromtimestamp(
                    stamp / 1000 if stamp > 1e12 else stamp,
                    timezone.utc).strftime("%Y-%m-%d")
            dates.append(str(stamp))
        if dates and (last is None or max(dates) > last):
            last = max(dates)
    return {"files": len(names), "empty": empty, "last_bar": last}


def main():
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    hour = now.strftime("%H00")
    slot = now.strftime("%Y-%m-%d %H:00")
    beat = json.load(open(HEARTBEAT)) if os.path.exists(HEARTBEAT) else {}
    per_asset = {asset: series(asset) for asset in ASSETS}
    payload = {
        "item": "Q4",
        "slot": slot,
        "oi_pc_ratio": per_asset,
        "market_backfill_remaining": beat.get("remaining"),
        "market_backfill_cycles": beat.get("cycles"),
        "market_backfill_phase": beat.get("phase"),
        "market_backfill_pid": beat.get("pid"),
    }
    path = write_result(
        f"q4_oi_pc_{hour}", payload, inputs=["data/laevitas/market"])
    print(path)
    still_short = any(
        row["last_bar"] is None or row["last_bar"] <= CUTOFF
        for row in per_asset.values())
    if not still_short:
        raise SystemExit("the series now extends past 2025-06; not marking blocked")
    note = (
        f" Rechecked {slot} UTC: results/{today}_q4_oi_pc_{hour}.json shows "
        f"oi_pc_ratio BTC {per_asset['BTC']['files']} files, "
        f"{per_asset['BTC']['empty']} empty, last bar "
        f"{per_asset['BTC']['last_bar']}; ETH {per_asset['ETH']['files']} "
        f"files, {per_asset['ETH']['empty']} empty, last bar "
        f"{per_asset['ETH']['last_bar']}. market_backfill reports remaining "
        f"{payload['market_backfill_remaining']} at cycle "
        f"{payload['market_backfill_cycles']}, phase "
        f"{payload['market_backfill_phase']}, so the walk is finished and "
        f"the vendor returned nothing later. Blocked on the series. {ANCHOR}"
    )
    text = open(BACKLOG).read()
    if note.strip() in text:
        print("note already present")
        return
    line = next(ln for ln in text.splitlines() if ln.startswith("- Q4. "))
    at = line.find(ANCHOR)
    if at < 0:
        raise SystemExit("anchor missing from the Q4 line")
    updated = line[:at] + ANCHOR + note + line[at + len(ANCHOR):]
    open(BACKLOG, "w").write(text.replace(line, updated, 1))
    print("noted")


if __name__ == "__main__":
    main()
