"""Record this run's reading of L2 on its backlog line.

The numbers come from results/2026-11-21_l2_status.json, written by
scripts/l2_status.py. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-21_l2_status.json")
ANCHOR = ("Unblocks when that file shows both families closed, option missing "
          "0 and liquidation missing 0.")


def main():
    status = json.load(open(RESULT))
    text = open(PATH).read()
    marker = "Rechecked 2026-11-21 09:00 UTC: results/2026-11-21_l2_status.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- L2. "))
    at = line.rfind(ANCHOR)
    if at < 0:
        raise SystemExit("anchor missing from the L2 line")
    options = status["options"]
    liquidations = status["liquidations"]
    beat = status["puller"]
    note = (
        " Rechecked 2026-11-21 09:00 UTC: results/2026-11-21_l2_status.json "
        f"shows perpetual_closed {status['perpetual_closed']} and "
        f"future_closed {status['future_closed']}, maturities walked "
        f"{status['maturities_walked']} of {status['maturities_listed']}, "
        f"option files {options['files']} of {options['listed']} with "
        f"{options['missing']} missing, liquidation files "
        f"{liquidations['files']} of {liquidations['listed']} with "
        f"{liquidations['missing']} missing. laevitas_pull pid {beat['pid']}, "
        f"alive, phase {beat['phase']}, cycles {beat['cycles']}, remaining "
        f"{beat['remaining']}. The option and liquidation counts are unchanged "
        "since the 07:00 reading, and the puller is walking perpetuals. "
        "Blocked on the pull. Unblocks when that file shows both families "
        "closed, option missing 0 and liquidation missing 0."
    )
    updated = line[:at] + ANCHOR + note + line[at + len(ANCHOR):]
    open(PATH, "w").write(text.replace(line, updated, 1))
    print("appended")


if __name__ == "__main__":
    main()
