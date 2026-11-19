"""Record where A5 stands, from the hourly store and the live heartbeat.

The Done-when clause needs health.rs_stale false for a full day. That flag is
computed by the live daemon from the newest bar in data/intraday, and it flips
true once that bar is more than three hours behind the clock. This script reads
both and writes the results file. It does not pull.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "data", "intraday")
HEARTBEAT = os.path.join(ROOT, "ops", "live_heartbeat")
STALE_AFTER = 3 * 3600


def store_ends():
    """The last bar time of every hourly file, as epoch seconds."""
    ends = {}
    for name in sorted(os.listdir(STORE)):
        if not name.endswith(".csv"):
            continue
        last = None
        with open(os.path.join(STORE, name)) as handle:
            for line in handle:
                if line[:1].isdigit():
                    last = line
        if last:
            ends[name[:-4]] = int(last.split(",")[0])
    return ends


def main():
    now = int(time.time())
    ends = store_ends()
    newest = max(ends.values()) if ends else None
    counts = {}
    for stamp in ends.values():
        key = datetime.fromtimestamp(stamp, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        counts[key] = counts.get(key, 0) + 1
    heartbeat = json.load(open(HEARTBEAT))
    age = (now - newest) if newest else None
    out = {
        "now": datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hourly_files": len(ends),
        "newest_bar": datetime.fromtimestamp(newest, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if newest else None,
        "newest_bar_age_sec": age,
        "rs_stale_now": age is None or age > STALE_AFTER,
        "stale_after_sec": STALE_AFTER,
        "bar_end_counts": counts,
        "live_daemon": {"pid": heartbeat.get("pid"), "version": heartbeat.get("version"),
                        "cycles": heartbeat.get("cycles"), "as_of": heartbeat.get("as_of"),
                        "heartbeat_ts": heartbeat.get("ts")},
        "full_day_not_yet_observed": True,
        "note": ("rs_stale is false at this reading because the newest hourly bar is "
                 "inside the three-hour window. The clause needs that for a full day, "
                 "and no earlier reading is on disk, so A5 is not done."),
    }
    path = write_result("a5_state", out, inputs=["data/intraday", "ops/live_heartbeat"])
    print(json.dumps({k: v for k, v in out.items() if k != "note"}))
    print(path)


if __name__ == "__main__":
    main()
