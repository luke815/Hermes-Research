"""Record this run's reading of L2 on its backlog line.

The numbers come from results/2026-11-21_l2_status.json, written by
scripts/l2_status.py. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-21_l2_status.json")
ANCHOR = "liquidation history saved for every venue and currency the puller lists."


def main():
    reading = json.load(open(RESULT))
    text = open(PATH).read()
    marker = "Rechecked 2026-11-21 00:00 UTC: results/2026-11-21_l2_status.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- L2. "))
    if not line.endswith(ANCHOR):
        raise SystemExit("anchor is not the end of the L2 line")
    puller = reading["puller"]
    note = (
        " Rechecked 2026-11-21 00:00 UTC: results/2026-11-21_l2_status.json "
        f"shows perpetual_closed {reading['perpetual_closed']} and future_closed "
        f"{reading['future_closed']}, maturities walked {reading['maturities_walked']} "
        f"of {reading['maturities_listed']}, option files {reading['options']['files']} "
        f"of {reading['options']['listed']} with {reading['options']['missing']} missing, "
        f"liquidation files {reading['liquidations']['files']} of "
        f"{reading['liquidations']['listed']} with {reading['liquidations']['missing']} "
        f"missing. laevitas_pull pid {puller.get('pid')}, alive, phase {puller.get('phase')}, "
        f"cycles {puller.get('cycles')}, remaining {puller.get('remaining')}. "
        "Blocked on the pull. Unblocks when that file shows both families closed, "
        "option missing 0 and liquidation missing 0."
    )
    open(PATH, "w").write(text.replace(line, line + note, 1))
    print("appended")


if __name__ == "__main__":
    main()
