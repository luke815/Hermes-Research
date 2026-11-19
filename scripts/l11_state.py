"""Record the L11 puller's state, from the files it has written.

The walk is a pull, so a research run does not run it. This counts the dead
names in the span files and the files the daemon has saved, and writes the
results file. It fetches nothing.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import delisted_pull  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    today = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%d")
    dead = delisted_pull.dead_names(today)
    saved = [name for name in os.listdir(delisted_pull.STORE)
             if name.endswith(".json")] if os.path.isdir(delisted_pull.STORE) else []
    per_venue = {}
    for row in dead:
        per_venue[row["market"]] = per_venue.get(row["market"], 0) + 1
    out = {
        "item": "L11",
        "today": today,
        "dead_names": len(dead),
        "dead_per_venue": per_venue,
        "files_saved": len(saved),
        "remaining": len(dead) - len(saved),
        "store": "data/laevitas/delisted",
        "daemon": "delisted_pull",
        "note": ("The puller walks the span files, one name per cycle. The merge "
                 "into panel_xs_laevitas waits until every dead name has a file."),
    }
    path = write_result("l11_pull", out, inputs=["data/binance_span.csv", "data/bybit_span.csv",
                                                  "data/okx_span.csv", "data/laevitas/delisted"])
    print(json.dumps({k: v for k, v in out.items() if k != "note"}))
    print(path)


if __name__ == "__main__":
    main()
