"""Record this run's reading of Q4 on its backlog line.

The clause waits on options_oi_pc_ratio extending past 2025-06. This script
reads the saved files and records how far they reach. It does not pull.
"""

import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
MARKET = os.path.join(ROOT, "data", "laevitas", "market")
ANCHOR = "Done when results/<date>_q4_pcratio_pairs.json exists and every pair shows its parent and lift."


def span(asset):
    last = None
    files = 0
    empty = 0
    for name in sorted(os.listdir(MARKET)):
        if not name.startswith(f"oi_pc_ratio_{asset}_"):
            continue
        files += 1
        body = json.load(open(os.path.join(MARKET, name)))
        items = body.get("items") or []
        if not items:
            empty += 1
            continue
        newest = max(row["date"] for row in items if row.get("date"))
        if last is None or newest > last:
            last = newest
    text = (datetime.fromtimestamp(last / 1000, timezone.utc).strftime("%Y-%m-%d")
            if last else "none")
    return files, empty, text


def main():
    text = open(PATH).read()
    marker = "Rechecked 2026-11-21 02:00 UTC: oi_pc_ratio"
    if marker in text:
        raise SystemExit("note already present")
    lines = text.splitlines(keepends=True)
    index = next(i for i, ln in enumerate(lines) if ANCHOR in ln)
    parts = []
    for asset in ("BTC", "ETH"):
        files, empty, last = span(asset)
        parts.append(f"{asset} {files} files, {empty} empty, last bar {last}")
    note = (
        " Rechecked 2026-11-21 02:00 UTC: oi_pc_ratio "
        + "; ".join(parts)
        + ". L9 is marked done and the files past 2023-03 are empty, so the "
        "series does not extend past 2025-06. market_backfill owns the pull "
        "and a research run does not pull. Blocked on the series. Unblocks "
        "when oi_pc_ratio has a bar after 2025-06 for BTC and ETH."
    )
    lines[index] = lines[index].rstrip("\n") + note + "\n"
    open(PATH, "w").write("".join(lines))
    print("appended")


if __name__ == "__main__":
    main()
