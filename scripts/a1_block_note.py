"""Record why A1 cannot close this run, from the files on disk.

The funding sums are written by funding_sum.write_sum, called by the
funding_sum daemon, one live name per cycle. A research run does not pull,
so this script only counts. A1's panel swap waits on every live name having a
sum file, and the count of names still missing is the block.
"""

import json
import os
import sys

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUMS = os.path.join(ROOT, "data", "funding_sum")


def missing_live():
    """Live names whose daily funding sum has not been written yet."""
    universe = pd.read_csv(os.path.join(ROOT, "data", "universe.csv"))
    live = universe[universe.delisted == 0]
    have = set(os.listdir(SUMS)) if os.path.isdir(SUMS) else set()
    per_venue = {}
    missing = {}
    for row in live.itertuples():
        per_venue[row.exchange] = per_venue.get(row.exchange, 0) + 1
        if f"{row.exchange}_{row.symbol}.csv" not in have:
            missing[row.exchange] = missing.get(row.exchange, 0) + 1
    return {"live_names": int(len(live)), "live_per_venue": per_venue,
            "missing_sum_file": int(sum(missing.values())), "missing_per_venue": missing,
            "sum_files_on_disk": len(have)}


def main():
    out = missing_live()
    out["blocks"] = "A1"
    out["daemon"] = "funding_sum"
    out["unblocks_when"] = (
        "funding_sum_daemon has written a sum file for every live name, "
        "so missing_sum_file is 0, and a1_rewrite.py has then swapped "
        "data/panel_xs_sum over data/panel_xs through data_guard")
    path = write_result("a1_block", out, inputs=["data/universe.csv", "data/funding_sum"])
    print(json.dumps(out))
    print(path)


if __name__ == "__main__":
    main()
