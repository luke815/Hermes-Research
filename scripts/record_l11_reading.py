"""Record one recheck of L11.

The counts come from scripts/l11_coverage.py and scripts/l11_reading.py,
run in this same process. The slot is today's UTC hour, read from the
clock, never typed. This script records that reading. It does not pull
and it does not decide the item is done.

Usage: python3 scripts/record_l11_reading.py
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402
from l11_coverage import main as coverage_main  # noqa: E402
from l11_reading import main as reading_main  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "Blocked on the vendor's start date."


def main():
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    hour = now.strftime("%H00")
    slot = now.strftime("%Y-%m-%d %H:00")
    coverage_main()
    reading_main()
    coverage = json.load(open(os.path.join(
        ROOT, "results", f"{today}_l11_coverage.json")))
    reading = json.load(open(os.path.join(
        ROOT, "results", f"{today}_l11_reading.json")))
    beat_path = os.path.join(ROOT, "ops", "delisted_pull_heartbeat")
    beat = json.load(open(beat_path)) if os.path.exists(beat_path) else {}
    out = {
        "item": "L11",
        "slot": slot,
        "dead_names": coverage["dead_names"],
        "panel_files": coverage["panel_files"],
        "missing_file": coverage["missing_file"],
        "all_three_from_2021": coverage["all_three_from_2021"],
        "earliest_first_bar": coverage["earliest_first_bar"],
        "coverage_written_at": coverage["provenance"]["written_at"],
        "remaining": reading["remaining"],
        "daemon_remaining": reading["daemon_remaining"],
        "daemon_pid": beat.get("pid"),
        "phase": beat.get("phase"),
        "cycles": beat.get("cycles"),
        "blocked": "vendor start date",
        "unblocks": (
            "a vendor history earlier than the earliest first bar for the "
            "dead names, which a research run does not pull"),
    }
    path = write_result(
        f"l11_reading_{hour}", out,
        inputs=[f"results/{today}_l11_coverage.json",
                f"results/{today}_l11_reading.json",
                "ops/delisted_pull_heartbeat"])
    note = (
        f" Rechecked {slot} UTC: results/{today}_l11_coverage.json counts "
        f"{out['dead_names']} dead names, {out['panel_files']} panel files, "
        f"{out['missing_file']} missing, and {out['all_three_from_2021']} "
        f"names with funding, open interest and basis from 2021, earliest "
        f"{out['earliest_first_bar']}, written "
        f"{out['coverage_written_at']}. "
        f"results/{today}_l11_reading_{hour}.json shows remaining "
        f"{out['remaining']} of {out['dead_names']}. delisted_pull pid "
        f"{out['daemon_pid']}, phase {out['phase']}, cycles {out['cycles']}, "
        f"remaining {out['daemon_remaining']}. The vendor serves nothing "
        f"earlier. Blocked on the vendor's start date."
    )
    text = open(BACKLOG).read()
    if note.strip() in text:
        print(path)
        print("note already present")
        return
    line = next(ln for ln in text.splitlines() if ln.startswith("- L11. "))
    if ANCHOR not in line:
        raise SystemExit("anchor missing from the L11 line")
    updated = line.replace(ANCHOR, ANCHOR + note, 1)
    open(BACKLOG, "w").write(text.replace(line, updated, 1))
    print(path)
    print("noted")


if __name__ == "__main__":
    main()
