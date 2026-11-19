"""Record what the 05:35 slot did, from the scheduler log and the store.

The Done-when clause needs the 05:35 slot to have refilled a real deleted day.
The scheduler writes its own record over results/<date>_laevitas_refresh.json,
so this reads the log line, the gap files and the window still missing, and
writes its own results file. It does not run the refresh, which pulls.
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from regime_tester.results_io import write_result  # noqa: E402
import laevitas_refresh as refresh  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "ops", "logs", "scheduler.log")
RESULTS = os.path.join(ROOT, "results")


def slot_lines():
    """Scheduler cycles that ran the refresh job."""
    out = []
    for line in open(LOG):
        if "scheduler: cycle" in line and " ok in " in line and "laevitas_refresh" in line:
            out.append(line.strip())
    return out


def gap_days():
    """Days sitting in a gap file, which only a refill writes."""
    out = {}
    for stem, _route in refresh.SERIES:
        path = os.path.join(refresh.STORE, f"{stem}_gap.json")
        if not os.path.exists(path):
            out[stem] = []
            continue
        rows = json.load(open(path))
        out[stem] = sorted({refresh._day(row["date"]) for row in rows if row.get("date")})
    return out


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    files = sorted(name for name in os.listdir(RESULTS) if name.endswith("_laevitas_refresh.json"))
    gaps = gap_days()
    still_missing = {stem: refresh.missing(stem, today) for stem, _route in refresh.SERIES}
    refilled = {stem: days for stem, days in gaps.items() if days}
    out = {
        "item": "L10",
        "today": today,
        "slot_cycles": slot_lines(),
        "slot_ran": bool(slot_lines()),
        "refresh_results_files": files,
        "gap_days": gaps,
        "refilled_stems": sorted(refilled),
        "still_missing": still_missing,
        "window_complete": not any(still_missing.values()),
    }
    path = write_result("l10_slot", out, inputs=["ops/logs/scheduler.log", "data/raw"])
    print(json.dumps({k: out[k] for k in ("today", "slot_ran", "refilled_stems", "window_complete")}))
    print(path)


if __name__ == "__main__":
    main()
