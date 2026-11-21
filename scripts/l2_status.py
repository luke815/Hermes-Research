"""Where L2 stands, read from the puller's own files.

The clause asks for the four families closed: perpetuals and futures stamped,
every catalogue maturity walked, option history saved for every listed
contract, and liquidation history saved for every venue and currency the
puller lists. This counts those and writes the reading. It does not pull.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from laevitas_pull import (  # noqa: E402
    FUTURES_STORE, LIQUIDATIONS_STORE, OPTIONS_STORE, STORE,
    family_closed, liquidation_rows, maturity_keys, option_rows,
    walked_maturities,
)
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def saved_count(store, rows):
    """How many of the listed rows have a file, and how many have none."""
    have = 0
    for row in rows:
        path = os.path.join(store, f"{row['market']}_{row['instrument']}.json")
        if os.path.exists(path):
            have += 1
    return {"listed": len(rows), "files": have, "missing": len(rows) - have}


def main():
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    walked = {tuple(row) for row in walked_maturities()}
    keys = [tuple(key) for key in maturity_keys()]
    heartbeat_path = os.path.join(ROOT, "ops", "laevitas_pull_heartbeat")
    heartbeat = json.load(open(heartbeat_path)) if os.path.exists(heartbeat_path) else {}
    out = {
        "item": "L2",
        "today": today,
        "perpetual_closed": family_closed("perpetual", STORE, today),
        "future_closed": family_closed("future", FUTURES_STORE, today),
        "maturities_listed": len(keys),
        "maturities_walked": sum(1 for key in keys if key in walked),
        "maturities_unwalked": sum(1 for key in keys if key not in walked),
        "options": saved_count(OPTIONS_STORE, option_rows()),
        "liquidations": saved_count(LIQUIDATIONS_STORE, liquidation_rows()),
        "puller": {
            "pid": heartbeat.get("pid"),
            "phase": heartbeat.get("phase"),
            "cycles": heartbeat.get("cycles"),
            "remaining": heartbeat.get("remaining"),
            "ts": heartbeat.get("ts"),
        },
    }
    path = write_result("l2_status", out, inputs=[
        "data/laevitas/family_closed.json", "data/laevitas/catalog_v1.json",
        "data/laevitas/option_maturities.json", "data/laevitas/option_contracts.json",
        "data/laevitas/instruments.json", "ops/laevitas_pull_heartbeat"])
    print(path)


if __name__ == "__main__":
    main()
