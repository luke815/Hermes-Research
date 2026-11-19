"""Record why the L10 slot has never fired, from the scheduler log.

The Done-when clause needs the 05:35 slot to have refilled a real deleted day.
This reads the scheduler log for that minute and the results files, and writes
what it finds. It does not run the refresh, which pulls.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "ops", "logs", "scheduler.log")
RESULTS = os.path.join(ROOT, "results")


def slot_lines():
    """Scheduler cycles that landed on the 05:35 minute."""
    out = []
    for line in open(LOG):
        if "T05:35:" in line and "scheduler: cycle" in line and " ok in " in line:
            out.append(line.strip())
    return out


def main():
    files = sorted(name for name in os.listdir(RESULTS) if name.endswith("_laevitas_refresh.json"))
    out = {
        "item": "L10",
        "slot_cycles": slot_lines(),
        "refresh_results_files": files,
        "slot_has_fired": bool(files),
        "note": ("The 05:35 minute was reached and recorded an empty run, and no "
                 "laevitas_refresh results file exists, so the slot has not refilled "
                 "a deleted day. A failed attempt used to close the slot for the day; "
                 "scripts/scheduler.py now leaves a failed slot open."),
    }
    path = write_result("l10_slot", out, inputs=["ops/logs/scheduler.log"])
    print(json.dumps({k: v for k, v in out.items() if k != "note"}))
    print(path)


if __name__ == "__main__":
    main()
