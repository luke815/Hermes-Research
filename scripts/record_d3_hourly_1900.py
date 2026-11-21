"""Record the 19:00 reading of D3 on its backlog line.

The reading is whether the hourly file and the hourly store exist. This
script checks both and writes the counts through write_result, then
appends the block note. It does not pull.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOURLY = os.path.join(ROOT, "research", "outside", "data", "hourly.pkl")
STORE = os.path.join(ROOT, "research", "outside", "data", "laevitas")
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "Unblocks when hourly.pkl exists or the harness masks the window and says so."


def hourly_csvs():
    if not os.path.isdir(STORE):
        return 0
    return sum(1 for name in os.listdir(STORE)
               if "hour" in name.lower() and name.endswith(".csv"))


def main():
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    exists = os.path.exists(HOURLY)
    csvs = hourly_csvs()
    payload = {
        "item": "D3",
        "today": today,
        "slot": "19:00",
        "hourly_pkl": exists,
        "laevitas_dir": os.path.isdir(STORE),
        "hourly_csvs": csvs,
    }
    path = write_result("d3_hourly_1900", payload, inputs=["research/outside"])
    print(path)
    if exists or csvs:
        raise SystemExit("hourly files appeared; not marking blocked")
    text = open(BACKLOG).read()
    marker = f"Rechecked {today} 19:00 UTC: results/{today}_d3_hourly_1900.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- D3. "))
    at = line.rfind(ANCHOR)
    if at < 0:
        raise SystemExit("anchor missing from the D3 line")
    note = (
        f" Rechecked {today} 19:00 UTC: results/{today}_d3_hourly_1900.json "
        "shows hourly.pkl absent and the laevitas hourly directory absent, so "
        "there are 0 hourly CSVs, nothing to mask and nothing to backfill "
        "from. No registered daemon pulls the Laevitas hourly store, and a "
        "research run does not pull. Blocked on the hourly files. Unblocks "
        "when hourly.pkl exists or the harness masks the window and says so."
    )
    updated = line[:at] + ANCHOR + note + line[at + len(ANCHOR):]
    open(BACKLOG, "w").write(text.replace(line, updated, 1))
    print("noted")


if __name__ == "__main__":
    main()
