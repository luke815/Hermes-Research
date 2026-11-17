"""Walk the OKX funding archive and store the daily sum, one day per cycle.

The archive zips hold every settlement. The saved store keeps the last print
and the mean, and neither is the sum. This reads one day, adds the numeric
settlements per stopped name, writes that day, and returns. A killed run
resumes from the days already recorded.
"""

import csv
import json
import os
import sys

# procmgr restarts from a clean environment, which does not have the user
# site on its path. The libraries live there, so the script adds them itself.
_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from funding_sum import _append_sum, okx_archive_day  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "data", "okx_funding_index.csv")
SPAN = os.path.join(ROOT, "data", "okx_span.csv")
PROGRESS = os.path.join(ROOT, "ops", "okx_archive.json")


def stopped():
    return {row["symbol"] for row in csv.DictReader(open(SPAN)) if row["stopped"] == "1"}


def done():
    if not os.path.exists(PROGRESS):
        return set()
    return set(json.load(open(PROGRESS)).get("done", []))


def cycle(ctx):
    """A batch of archived days, then return. A day is recorded only after it is written."""
    have = done()
    pending = [(day, url) for day, url in csv.reader(open(INDEX)) if day not in have]
    if not pending:
        return {"remaining": 0}
    symbols = stopped()
    written = 0
    last = None
    for day, url in pending[:40]:
        sums = okx_archive_day(day, url, symbols)
        for base, values in sums.items():
            if not values:
                continue
            _append_sum("okx_archive", base, day, values)
            written += 1
        have.add(day)
        tmp = PROGRESS + ".tmp"
        json.dump({"done": sorted(have)}, open(tmp, "w"))
        os.replace(tmp, PROGRESS)
        last = day
    return {"day": last, "names": written, "remaining": len(pending) - 40}


if __name__ == "__main__":
    from daemon_base import run_loop
    run_loop("okx_funding_sum", interval_sec=900, cycle=cycle, align=False, max_cycle_sec=1200)
