"""Where X1 stands, read from the sweep status line and the heartbeat.

The clause needs the status line to show the panel's name count and cells per
hour above 5,000 for one full hour. Both numbers are written by the sweep
itself, so this script only reads them.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    line = open(os.path.join(ROOT, "ops", "sweep_status")).read().strip()
    heartbeat = json.load(open(os.path.join(ROOT, "ops", "sweep_xs_heartbeat")))
    panel = os.path.join(ROOT, "data", "panel_xs_laevitas")
    out = {
        "item": "X1",
        "status_line": line,
        "panel_files": len([n for n in os.listdir(panel) if n.endswith(".csv")]),
        "sweep": {"pid": heartbeat.get("pid"), "version": heartbeat.get("version"),
                  "phase": heartbeat.get("phase"), "cycles": heartbeat.get("cycles"),
                  "names": heartbeat.get("names"), "remaining": heartbeat.get("remaining"),
                  "ts": heartbeat.get("ts")},
        "cells_per_hour_above_5000": "cells per hour" in line and _rate(line) > 5000,
    }
    path = write_result("x1_status", out, inputs=["ops/sweep_status", "ops/sweep_xs_heartbeat"])
    print(json.dumps(out, indent=1))
    print(path)


def _rate(line):
    try:
        return int(line.split("cells per hour", 1)[1].split(",")[0].strip())
    except (IndexError, ValueError):
        return 0


if __name__ == "__main__":
    main()
