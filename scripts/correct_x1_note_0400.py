"""Correct the 04:00 X1 note, which cited a stale status file.

scripts/x1_status.py rewrote results/2026-11-21_x1_status.json from a heartbeat
left by the stopped process, and its range count of 0 came from that run. This
script reads the panel files and the live heartbeat and replaces that note.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
OLD = "Rechecked 2026-11-21 04:00 UTC: results/2026-11-21_x1_status.json shows cells per hour 0, names 234, 19872 emittable cells still open, 4752 market-level and 15120 that need high and low. scripts/copy_range.py copied high and low from data/panel_xs and data_guard swapped the directory in, results/2026-11-21_swap_data__panel_xs_laevitas.json, previous kept as data/panel_xs_laevitas.prev-20261121T042846Z. 776 of 5538 files now carry the columns, but the donor panel holds only a handful of dates per name, so the range measures stay unscoreable. scripts/sweep_xs.py now reads high and low when a file has them, tests/test_sweep_range.py, and the daemon was restarted onto that commit. The columns are not on disk in any depth. Blocked on the range columns reaching the panel the sweep reads. Unblocks when ops/sweep_status shows cells per hour above 5,000."


def main():
    panel = os.path.join(ROOT, "data", "panel_xs_laevitas")
    files = [n for n in os.listdir(panel) if n.endswith(".csv")]
    with_range = sum(1 for name in files
                     if "high" in open(os.path.join(panel, name)).readline())
    heartbeat = json.load(open(os.path.join(ROOT, "ops", "sweep_xs_heartbeat")))
    status = open(os.path.join(ROOT, "ops", "sweep_status")).read().strip()
    text = open(PATH).read()
    if OLD not in text:
        raise SystemExit("old note not found")
    note = (
        "Rechecked 2026-11-21 04:00 UTC: ops/sweep_status reads "
        f"'{status}'. data/panel_xs_laevitas has high and low on {with_range} "
        f"of {len(files)} files. scripts/copy_range.py copied them from "
        "data/panel_xs and data_guard swapped the directory in, "
        "results/2026-11-21_swap_data__panel_xs_laevitas.json, previous kept "
        "as data/panel_xs_laevitas.prev-20261121T042846Z. The donor panel holds "
        "only a handful of dates per name, so the range measures stay "
        "unscoreable. scripts/sweep_xs.py now reads high and low when a file "
        "has them, tests/test_sweep_range.py. sweep_xs pid "
        f"{heartbeat.get('pid')}, alive, phase {heartbeat.get('phase')}, "
        f"version {heartbeat.get('version')}, cycles {heartbeat.get('cycles')}. "
        "Blocked on the range columns reaching the panel the sweep reads in "
        "any depth. Unblocks when ops/sweep_status shows cells per hour above "
        "5,000."
    )
    open(PATH, "w").write(text.replace(OLD, note, 1))
    print(json.dumps({"files": len(files), "with_range": with_range,
                      "pid": heartbeat.get("pid"), "phase": heartbeat.get("phase"),
                      "version": heartbeat.get("version")}))


if __name__ == "__main__":
    main()
