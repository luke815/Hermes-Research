"""Read the L11 daemon and write this run's coverage counts.

A research run does not pull. This script reads the delisted_pull heartbeat
and the span files, then writes the counts through write_result. It does not
decide the item is done.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone  # noqa: E402

from delisted_pull import dead_names, done, path_for  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def reading(today):
    names = dead_names(today)
    remaining = sum(1 for row in names if not done(path_for(row), today))
    heartbeat = {}
    path = os.path.join(ROOT, "ops", "delisted_pull_heartbeat")
    if os.path.exists(path):
        heartbeat = json.load(open(path))
    return {
        "item": "L11",
        "today": today,
        "dead_names": len(names),
        "remaining": remaining,
        "daemon_alive": bool(heartbeat),
        "phase": heartbeat.get("phase"),
        "cycles": heartbeat.get("cycles"),
        "daemon_remaining": heartbeat.get("remaining"),
    }


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = write_result("l11_reading", reading(today), inputs=[
        "data/binance_span.csv", "data/bybit_span.csv", "data/okx_span.csv",
        "data/laevitas/delisted"])
    print(path)


if __name__ == "__main__":
    main()
