"""Count the delisted names still waiting for a saved history.

The puller writes one file per name into data/laevitas/delisted, and a
saved empty answer counts as done. This script only counts, so a research
run can see how far the walk is without pulling.
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import delisted_pull  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dead = delisted_pull.dead_names(today)
    left = delisted_pull.pending(today)
    saved = len(dead) - len(left)
    out = {"dead_names": len(dead), "saved": saved, "remaining": len(left),
           "store": "data/laevitas/delisted"}
    path = write_result("l11_pull", out,
                        inputs=["data/binance_span.csv", "data/bybit_span.csv",
                                "data/okx_span.csv", "data/laevitas/delisted"])
    print(json.dumps(out))
    print(path)


if __name__ == "__main__":
    main()
