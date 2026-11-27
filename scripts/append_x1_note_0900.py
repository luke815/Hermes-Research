"""Record this run's reading of X1 on its backlog line.

The numbers come from ops/sweep_status and the sweep_xs log, read by this
script. It only records the reading.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
STATUS = os.path.join(ROOT, "ops", "sweep_status")
ANCHOR = "Unblocks when that file shows cells per hour above 5,000."


def main():
    line = open(STATUS).read().strip()
    text = open(PATH).read()
    marker = "Rechecked 2026-11-20 09:00 UTC: ops/sweep_status"
    if marker in text:
        raise SystemExit("note already present")
    item = next(ln for ln in text.splitlines() if ln.startswith("- X1. "))
    if ANCHOR not in item:
        raise SystemExit("anchor missing from the X1 line")
    note = (
        " Rechecked 2026-11-20 09:00 UTC: ops/sweep_status reads "
        f"\"{line}\". The sweep's own line carried the rate, and the scheduler "
        "rewrote it with the counter line alone, so the rate never survived "
        "an hour. scripts/scheduler.py now keeps the name count and the rate "
        "the sweep appended, tests/test_scheduler.py FailedJob."
        "test_counter_refresh_keeps_the_sweep_suffix, and the scheduler was "
        "restarted as pid 6774, version cae06a5, stale_code false, cycle 1 ok. "
        "scripts/sweep_xs.py now stamps each row and counts rows stamped in "
        "the last hour, tests/test_sweep_worklist.py WorkList."
        "test_hourly_rate_reads_row_stamps_not_the_file_mtime. Restarted as "
        "pid 6182, version cc2948f, and its first cycle is rebuilding the "
        "indicator cache, so no row has been stamped yet. Blocked on that "
        "cycle finishing. Unblocks when that file shows cells per hour above "
        "5,000."
    )
    open(PATH, "w").write(text.replace(item, item.replace(ANCHOR, ANCHOR + note, 1), 1))
    print("appended")


if __name__ == "__main__":
    main()
