"""Record the current health.rs_stale and how long it has stayed false.

Reads dashboard/live.json, which the live daemon rewrites every cycle, appends
the reading to ops/rs_stale_log.jsonl and writes the results file. A5's clause
needs the flag false for a full day, so the span is the thing to read. This
script does not pull and does not decide the item is done.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402
from regime_tester.rs_stale_log import LOG, append, false_span_hours, read  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(ROOT, "dashboard", "live.json")


def main():
    payload = json.load(open(LIVE))
    health = payload["health"]
    ts = health["daemon_heartbeat"]
    added = append(LOG, ts, health["rs_stale"], health.get("rs_age_sec"))
    rows = read(LOG)
    span = false_span_hours(rows)
    out = {
        "reading_ts": ts,
        "appended": added,
        "rs_stale": health["rs_stale"],
        "rs_age_sec": health.get("rs_age_sec"),
        "board_as_of": payload.get("relative_strength", {}).get("as_of"),
        "readings": len(rows),
        "false_span_hours": span,
        "full_day": span is not None and span >= 24,
    }
    path = write_result("a5_span", out, inputs=["dashboard/live.json", "ops/rs_stale_log.jsonl"])
    print(json.dumps(out))
    print(path)


if __name__ == "__main__":
    main()
