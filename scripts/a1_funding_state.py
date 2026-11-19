"""Record how far the funding sums are, from the files on disk.

The daemon writes one file per live name. This counts them and writes the
results file. It fetches nothing.
"""

import json
import os
import sys

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd  # noqa: E402
import funding_sum_daemon  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    universe = pd.read_csv(os.path.join(ROOT, "data", "universe.csv"))
    live = universe[universe.delisted == 0]
    have = set(os.listdir(funding_sum_daemon.OUT)) if os.path.isdir(funding_sum_daemon.OUT) else set()
    per_venue = {}
    missing = {}
    for exchange, group in live.groupby("exchange"):
        wanted = {f"{exchange}_{symbol}.csv" for symbol in group.symbol}
        found = wanted & have
        per_venue[exchange] = {"live": int(len(group)), "summed": len(found)}
        missing[exchange] = int(len(wanted - found))
    left = funding_sum_daemon.pending()
    out = {
        "item": "A1",
        "live_names": int(len(live)),
        "per_venue": per_venue,
        "missing_per_venue": missing,
        "remaining": len(left),
        "store": "data/funding_sum",
    }
    path = write_result("a1_block", out, inputs=["data/universe.csv", "data/funding_sum"])
    print(json.dumps({"live_names": out["live_names"], "remaining": out["remaining"],
                      "missing_per_venue": missing}))
    print(path)


if __name__ == "__main__":
    main()
