"""Record the 00:00 A7 reading on the backlog line.

A7(1) is no longer blocked. A7(3) stays blocked until derivs_summary has a
file for all five alts. The note is built from the reading this script's
sibling wrote, and it is inserted before the item header.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
READING = os.path.join(ROOT, "results", "2026-11-22_a7_block_0000.json")
HEADER = "- A7. "


def main():
    reading = json.load(open(READING))
    if reading["a7_1_blocked"]:
        raise SystemExit("A7(1) is blocked; this note says it is not")
    missing = reading["alts_missing"]
    if not missing:
        raise SystemExit("no alt is missing; this note is the blocked reading")
    text = open(PATH).read()
    if text.count(HEADER) != 1:
        raise SystemExit(f"header count {text.count(HEADER)}")
    note = (
        f"Rechecked 2026-11-22 00:00 UTC: {READING.split(ROOT + os.sep, 1)[1]} "
        f"shows the close on 2026-01-13 is {reading['close_2026_01_13']} against "
        f"{reading['close_2026_01_12']} on 2026-01-12 and {reading['close_2026_01_14']} "
        f"on 2026-01-14, file mtime {reading['panel_mtime']}. A7(1) is not blocked. "
        f"A7(3) stays blocked: derivs_summary covers "
        f"{', '.join(reading['derivs_summary_currencies'])} and not "
        f"{', '.join(missing)}. market_backfill is walking the five alts, "
        f"phase {reading['market_backfill_phase']}, cycle "
        f"{reading['market_backfill_cycles']}. Unblocks when derivs_summary has "
        "a file for ADA, SOL, LINK, XRP and AVAX. A research run does not pull. "
    )
    open(PATH, "w").write(text.replace(HEADER, HEADER + note, 1))
    print("appended", len(note))


if __name__ == "__main__":
    main()
