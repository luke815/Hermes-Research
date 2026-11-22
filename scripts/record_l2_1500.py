"""Record the 15:00 reading of L2.

The counts come from results/2026-11-22_l2_status.json, written by
scripts/l2_status.py. This script records the reading. It does not pull
and it does not decide the item is done.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUS = os.path.join(ROOT, "results", "2026-11-22_l2_status.json")
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
SLOT = "2026-11-22 15:00"
ANCHOR = ("Unblocks when that file shows both families closed, option "
          "missing 0 and liquidation missing 0.")


def main():
    status = json.load(open(STATUS))
    options = status["options"]
    liquidations = status["liquidations"]
    puller = status["puller"]
    out = {
        "item": "L2",
        "slot": SLOT,
        "perpetual_closed": status["perpetual_closed"],
        "future_closed": status["future_closed"],
        "maturities_walked": status["maturities_walked"],
        "maturities_listed": status["maturities_listed"],
        "option_files": options["files"],
        "option_listed": options["listed"],
        "option_missing": options["missing"],
        "liquidation_files": liquidations["files"],
        "liquidation_listed": liquidations["listed"],
        "liquidation_missing": liquidations["missing"],
        "puller_pid": puller["pid"],
        "phase": puller["phase"],
        "cycles": puller["cycles"],
        "remaining": puller["remaining"],
        "blocked": "pull",
        "unblocks": (
            "results/2026-11-22_l2_status.json shows both families closed, "
            "option missing 0 and liquidation missing 0"),
    }
    path = write_result(
        "l2_reading_1500", out, inputs=["results/2026-11-22_l2_status.json"])
    print(path)
    if (status["perpetual_closed"] and status["future_closed"]
            and options["missing"] == 0 and liquidations["missing"] == 0):
        raise SystemExit("the pull finished; not marking blocked")
    note = (
        f" Rechecked {SLOT} UTC: results/2026-11-22_l2_status.json shows "
        f"perpetual_closed {status['perpetual_closed']} and future_closed "
        f"{status['future_closed']}, maturities walked "
        f"{status['maturities_walked']} of {status['maturities_listed']}, "
        f"option files {options['files']} of {options['listed']} with "
        f"{options['missing']} missing, liquidation files "
        f"{liquidations['files']} of {liquidations['listed']} with "
        f"{liquidations['missing']} missing. results/2026-11-22_l2_reading_"
        f"1500.json shows remaining {puller['remaining']}. laevitas_pull pid "
        f"{puller['pid']}, phase {puller['phase']}, cycles {puller['cycles']}, "
        f"remaining {puller['remaining']}. The option and liquidation counts "
        f"are unchanged since the 13:00 note. Blocked on the pull. {ANCHOR}"
    )
    text = open(BACKLOG).read()
    if note.strip() in text:
        print("note already present")
        return
    line = next(ln for ln in text.splitlines() if ln.startswith("- L2. "))
    if ANCHOR not in line:
        raise SystemExit("anchor missing")
    updated = line.replace(ANCHOR, ANCHOR + note, 1)
    open(BACKLOG, "w").write(text.replace(line, updated, 1))
    print("noted")


if __name__ == "__main__":
    main()
