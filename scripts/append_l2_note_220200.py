"""Append the 02:00 reading of L2 to its backlog line.

The numbers come from results/2026-11-22_l2_status.json, written by
scripts/l2_status.py, and the prior remaining count comes from
results/2026-11-21_l2_status.json. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-22_l2_status.json")
PRIOR = os.path.join(ROOT, "results", "2026-11-21_l2_status.json")


def main():
    reading = json.loads(open(RESULT).read())
    prior = json.loads(open(PRIOR).read())
    puller = reading["puller"]
    marker = (
        f"Rechecked {reading['today']} 02:00 UTC: "
        f"results/{reading['today']}_l2_status.json")
    text = open(PATH).read()
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- L2. "))
    if not line.endswith("liquidation missing 0."):
        raise SystemExit("the L2 line no longer ends on the unblock sentence")
    note = (
        f" Rechecked {reading['today']} 02:00 UTC: "
        f"results/{reading['today']}_l2_status.json shows perpetual_closed "
        f"{reading['perpetual_closed']} and future_closed "
        f"{reading['future_closed']}, maturities walked "
        f"{reading['maturities_walked']} of {reading['maturities_listed']}, "
        f"option files {reading['options']['files']} of "
        f"{reading['options']['listed']} with {reading['options']['missing']} "
        f"missing, liquidation files {reading['liquidations']['files']} of "
        f"{reading['liquidations']['listed']} with "
        f"{reading['liquidations']['missing']} missing. laevitas_pull pid "
        f"{puller['pid']}, alive, phase {puller['phase']}, cycles "
        f"{puller['cycles']}, remaining {puller['remaining']}. The option and "
        f"liquidation counts are unchanged since the 19:00 reading, and "
        f"remaining fell from {prior['puller']['remaining']} to "
        f"{puller['remaining']}. Blocked on the pull. Unblocks when that file "
        f"shows both families closed, option missing 0 and liquidation "
        f"missing 0.")
    open(PATH, "w").write(text.replace(line, line + note, 1))
    print("appended", reading["options"]["missing"], puller["remaining"])


if __name__ == "__main__":
    main()
