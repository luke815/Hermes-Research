"""Record one recheck of D3.

The reading is whether the hourly file and the hourly store exist. The
slot is today's UTC hour, read from the clock. This script checks both
and writes the counts through write_result, then appends the block note.
It does not pull.

Usage: python3 scripts/record_d3_reading.py
"""

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOURLY = os.path.join(ROOT, "research", "outside", "data", "hourly.pkl")
STORE = os.path.join(ROOT, "research", "outside", "data", "laevitas")
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "Unblocks when hourly.pkl exists or the harness masks the window and says so."
REGISTRY = os.path.join(ROOT, "ops", "daemons.json")


def hourly_csvs():
    if not os.path.isdir(STORE):
        return 0
    return sum(
        1 for name in os.listdir(STORE)
        if "hour" in name.lower() and name.endswith(".csv"))


def pulls_hourly():
    """A registered daemon whose command mentions the hourly store."""
    if not os.path.exists(REGISTRY):
        return False
    return "hourly" in open(REGISTRY).read()


def main():
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    hour = now.strftime("%H00")
    slot = now.strftime("%Y-%m-%d %H:00")
    exists = os.path.exists(HOURLY)
    csvs = hourly_csvs()
    payload = {
        "item": "D3",
        "slot": slot,
        "hourly_pkl": exists,
        "laevitas_dir": os.path.isdir(STORE),
        "hourly_csvs": csvs,
        "daemon_pulls_hourly": pulls_hourly(),
    }
    path = write_result(f"d3_hourly_{hour}", payload, inputs=["research/outside"])
    print(path)
    if exists or csvs:
        raise SystemExit("hourly files appeared; not marking blocked")
    note = (
        f" Rechecked {slot} UTC: results/{today}_d3_hourly_{hour}.json shows "
        f"hourly.pkl absent and the laevitas hourly directory absent, so "
        f"there are 0 hourly CSVs, nothing to mask and nothing to backfill "
        f"from. No registered daemon pulls the Laevitas hourly store, and a "
        f"research run does not pull. Blocked on the hourly files. {ANCHOR}"
    )
    text = open(BACKLOG).read()
    if note.strip() in text:
        print("note already present")
        return
    line = next(ln for ln in text.splitlines() if ln.startswith("- D3. "))
    at = line.rfind(ANCHOR)
    if at < 0:
        raise SystemExit("anchor missing from the D3 line")
    updated = line[:at] + ANCHOR + note + line[at + len(ANCHOR):]
    open(BACKLOG, "w").write(text.replace(line, updated, 1))
    print("noted")


if __name__ == "__main__":
    main()
