"""Append this run's reading of L2 to its backlog line.

The numbers come from results/2026-11-21_l2_status.json, written by
scripts/l2_status.py. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-21_l2_status.json")


def main():
    reading = json.loads(open(RESULT).read())
    puller = reading["puller"]
    marker = f"Rechecked {reading['today']} 19:00 UTC: results/{reading['today']}_l2_status.json"
    text = open(PATH).read()
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- L2. "))
    note = (
        f" Rechecked {reading['today']} 19:00 UTC: results/{reading['today']}_l2_status.json "
        f"shows perpetual_closed {reading['perpetual_closed']} and future_closed "
        f"{reading['future_closed']}, maturities walked {reading['maturities_walked']} of "
        f"{reading['maturities_listed']}, option files {reading['options']['files']} of "
        f"{reading['options']['listed']} with {reading['options']['missing']} missing, "
        f"liquidation files {reading['liquidations']['files']} of "
        f"{reading['liquidations']['listed']} with {reading['liquidations']['missing']} missing. "
        f"laevitas_pull pid {puller['pid']}, alive, phase {puller['phase']}, cycles "
        f"{puller['cycles']}, remaining {puller['remaining']}. The option and liquidation "
        f"counts are unchanged since the 13:00 reading. Blocked on the pull. Unblocks when "
        f"that file shows both families closed, option missing 0 and liquidation missing 0.")
    open(PATH, "w").write(text.replace(line, line + note, 1))
    print("appended", reading["options"]["missing"], reading["liquidations"]["missing"])


if __name__ == "__main__":
    main()
