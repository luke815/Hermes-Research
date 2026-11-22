"""Record the 02:00 reading of the series that blocks Q4.

Q4 waits on oi_pc_ratio having a bar after 2025-06 for BTC and ETH. The
market_backfill daemon owns that pull, and a research run does not pull.
This counts the files and reads the daemon's heartbeat, writes them
through write_result, and appends the block note.
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
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    beat = {}
    if os.path.exists(HEARTBEAT):
        beat = json.load(open(HEARTBEAT))
    per_asset = {asset: series(asset) for asset in ASSETS}
    payload = {
        "item": "Q4",
        "today": today,
        "read_at": stamp,
        "slot": "02:00",
        "oi_pc_ratio": per_asset,
        "market_backfill_remaining": beat.get("remaining"),
        "market_backfill_cycles": beat.get("cycles"),
        "market_backfill_phase": beat.get("phase"),
    }
    path = write_result("q4_oi_pc_0200", payload, inputs=["data/laevitas/market"])
    print(path)
    still_short = any(
        row["last_bar"] is None or row["last_bar"] <= CUTOFF
        for row in per_asset.values())
    if not still_short:
        raise SystemExit("the series now extends past 2025-06; not marking blocked")
    text = open(BACKLOG).read()
    marker = f"Rechecked {today} 02:00 UTC: results/{today}_q4_oi_pc_0200.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- Q4. "))
    anchor = "Unblocks when oi_pc_ratio has a bar after 2025-06 for BTC and ETH."
    at = line.rfind(anchor)
    if at < 0:
        raise SystemExit("anchor missing from the Q4 line")
    btc = per_asset["BTC"]
    eth = per_asset["ETH"]
    note = (
        f" Rechecked {today} 02:00 UTC: results/{today}_q4_oi_pc_0200.json "
        f"shows oi_pc_ratio BTC {btc['files']} files, {btc['empty']} empty, "
        f"last bar {btc['last_bar']}; ETH {eth['files']} files, {eth['empty']} "
        f"empty, last bar {eth['last_bar']}. market_backfill reports remaining "
        f"{payload['market_backfill_remaining']} at cycle "
        f"{payload['market_backfill_cycles']}, phase "
        f"{payload['market_backfill_phase']}, so the walk is finished and the "
        "vendor returned nothing later. Blocked on the series. Unblocks when "
        "oi_pc_ratio has a bar after 2025-06 for BTC and ETH."
    )
    updated = line[:at] + anchor + note + line[at + len(anchor):]
    open(BACKLOG, "w").write(text.replace(line, updated, 1))
    print("noted")


if __name__ == "__main__":
    main()
