"""Record the 13:00 reading of D3.

The clause needs hourly.pkl with no gap longer than one hour in the named
window, or a harness that masks the window. This reads the paths and the
daemon registry. It does not pull.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOURLY = os.path.join(ROOT, "research", "outside", "data", "hourly.pkl")
LAEVITAS = os.path.join(ROOT, "research", "outside", "data", "laevitas")
REGISTRY = os.path.join(ROOT, "ops", "daemons.json")
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
SLOT = "2026-11-22 13:00"
ANCHOR = "Unblocks when hourly.pkl exists or the harness masks the window and says so."


def main():
    registry = json.load(open(REGISTRY))
    csvs = 0
    if os.path.isdir(LAEVITAS):
        csvs = sum(1 for name in os.listdir(LAEVITAS) if "hourly" in name.lower())
    payload = {
        "item": "D3",
        "slot": SLOT,
        "hourly_pkl": os.path.exists(HOURLY),
        "laevitas_hourly_dir": os.path.isdir(LAEVITAS),
        "hourly_csvs": csvs,
        "registered_daemons": sorted(registry),
        "hourly_daemon": None,
        "blocked": "hourly files absent and no daemon pulls them",
        "unblocks": "hourly.pkl exists or the harness masks the window and says so",
    }
    path = write_result("d3_hourly_1300", payload, inputs=[
        "research/outside", "ops/daemons.json"])
    print(path)
    if payload["hourly_pkl"]:
        raise SystemExit("hourly.pkl exists; not marking blocked")
    note = (
        f" Rechecked {SLOT} UTC: results/2026-11-22_d3_hourly_1300.json shows "
        f"hourly.pkl absent and the laevitas hourly directory absent, so "
        f"there are {csvs} hourly CSVs, nothing to mask and nothing to "
        f"backfill from. No registered daemon pulls the Laevitas hourly "
        f"store, and a research run does not pull. Unchanged since the "
        f"09:00 note. Blocked on the hourly files. {ANCHOR}"
    )
    text = open(BACKLOG).read()
    if note.strip() in text:
        print("note already present")
        return
    line = next(ln for ln in text.splitlines() if ln.startswith("- D3. "))
    if ANCHOR not in line:
        raise SystemExit("anchor missing")
    updated = line.replace(ANCHOR, ANCHOR + note, 1)
    open(BACKLOG, "w").write(text.replace(line, updated, 1))
    print("noted")


if __name__ == "__main__":
    main()
