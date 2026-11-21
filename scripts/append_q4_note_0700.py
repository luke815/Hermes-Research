"""Record this run's reading of Q4 on its backlog line.

The numbers come from results/2026-11-21_q4_oi_pc.json, written by
scripts/q4_oi_pc.py. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-21_q4_oi_pc.json")
ANCHOR = "Unblocks when oi_pc_ratio has a bar after 2025-06 for BTC and ETH."


def main():
    reading = json.load(open(RESULT))
    text = open(PATH).read()
    marker = "Rechecked 2026-11-21 07:00 UTC: results/2026-11-21_q4_oi_pc.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- Q4. "))
    if ANCHOR not in line:
        raise SystemExit("anchor missing from the Q4 line")
    btc, eth = reading["btc"], reading["eth"]
    note = (
        " Rechecked 2026-11-21 07:00 UTC: results/2026-11-21_q4_oi_pc.json "
        f"shows oi_pc_ratio BTC {btc['files']} files, {btc['empty']} empty, "
        f"last bar {btc['last_bar']}; ETH {eth['files']} files, {eth['empty']} "
        f"empty, last bar {eth['last_bar']}. market_backfill reports remaining "
        "0, so it has finished the walk and the vendor returned nothing later. "
        "Blocked on the series. Unblocks when oi_pc_ratio has a bar after "
        "2025-06 for BTC and ETH."
    )
    updated = line.replace(ANCHOR, ANCHOR + note, 1)
    open(PATH, "w").write(text.replace(line, updated, 1))
    print("appended")


if __name__ == "__main__":
    main()
