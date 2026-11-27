"""Record the 00:00 reading of A7 and the state of its inputs.

A7(1) was scored yesterday. A7(3) is blocked because derivs_summary has no
file for the five alts. This script reads the panel and the market store and
writes the reading; it does not score and it does not pull.
"""

import csv
import os
from datetime import datetime, timezone

from regime_tester.results_io import write_result

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs_laevitas", "binance_1000PEPEUSDT.csv")
MARKET = os.path.join(ROOT, "data", "laevitas", "market")
HEARTBEAT = os.path.join(ROOT, "ops", "market_backfill_heartbeat")
NAMES = ("ADA", "SOL", "LINK", "XRP", "AVAX")


def close_on(day):
    with open(PANEL) as handle:
        rows = {row["date"]: row["close"] for row in csv.DictReader(handle)}
    return float(rows[day])


def main():
    mtime = datetime.fromtimestamp(os.stat(PANEL).st_mtime, timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    covered = sorted({
        name.split("_")[2]
        for name in os.listdir(MARKET)
        if name.startswith("derivs_summary_") and name.endswith(".json")
    })
    missing = [name for name in NAMES if name not in covered]
    heartbeat = {}
    if os.path.exists(HEARTBEAT):
        import json
        heartbeat = json.load(open(HEARTBEAT))
    payload = {
        "item": "A7",
        "panel_file": "data/panel_xs_laevitas/binance_1000PEPEUSDT.csv",
        "panel_mtime": mtime,
        "close_2026_01_12": close_on("2026-01-12"),
        "close_2026_01_13": close_on("2026-01-13"),
        "close_2026_01_14": close_on("2026-01-14"),
        "derivs_summary_currencies": covered,
        "alts_missing": missing,
        "a7_1_blocked": False,
        "a7_3_blocked": bool(missing),
        "market_backfill_phase": heartbeat.get("phase"),
        "market_backfill_cycles": heartbeat.get("cycles"),
        "market_backfill_last_result": heartbeat.get("last_result"),
    }
    path = write_result("a7_block_0000", payload, inputs=[
        "data/panel_xs_laevitas/binance_1000PEPEUSDT.csv",
        "data/laevitas/market",
    ])
    print(path)
    print(payload["close_2026_01_13"], payload["alts_missing"],
          payload["market_backfill_cycles"])


if __name__ == "__main__":
    main()
