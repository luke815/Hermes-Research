"""Record one recheck of the inputs that block B5.

The 4-hour entry timing reads the hourly store and the book's legs. The
slot is today's UTC hour, read from the clock. This reads the dates and
writes them through write_result, then appends the block note. It does
not pull.

Usage: python3 scripts/record_b5_reading.py
"""

import glob
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
INTRADAY = os.path.join(ROOT, "data", "intraday")
LEGS = os.path.join(ROOT, "signals", "book.csv")
FRESH_DAYS = 2
ANCHOR = "Unblocks when the hourly files are current."


def main():
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    hour = now.strftime("%H00")
    slot = now.strftime("%Y-%m-%d %H:00")
    today_dt = datetime.strptime(today, "%Y-%m-%d")
    counts = Counter()
    for path in glob.glob(os.path.join(INTRADAY, "*.csv")):
        last = None
        with open(path) as handle:
            for line in handle:
                if line.strip():
                    last = line
        if last is None:
            continue
        stamp = int(float(last.split(",")[0]))
        day = datetime.fromtimestamp(stamp, timezone.utc).strftime("%Y-%m-%d")
        counts[day] += 1
    newest = max(counts) if counts else None
    fresh = sum(
        n for day, n in counts.items()
        if (today_dt - datetime.strptime(day, "%Y-%m-%d")).days <= FRESH_DAYS)
    out = {
        "item": "B5",
        "slot": slot,
        "hourly_files": sum(counts.values()),
        "hourly_newest": newest,
        "hourly_newest_age_days": (
            today_dt - datetime.strptime(newest, "%Y-%m-%d")).days,
        "hourly_fresh_files": fresh,
        "hourly_stale_files": sum(counts.values()) - fresh,
        "hourly_by_day": dict(sorted(counts.items())),
        "legs_file_exists": os.path.exists(LEGS),
        "legs_rows": sum(1 for _ in open(LEGS)) - 1 if os.path.exists(LEGS) else 0,
    }
    path = write_result(f"b5_inputs_{hour}", out, inputs=[
        "data/intraday/1000PEPEUSDT_PERP.A.csv", "signals/book.csv"])
    print(path)
    if out["hourly_stale_files"] == 0:
        raise SystemExit("hourly store is current; not marking blocked")
    note = (
        f" Rechecked {slot} UTC: results/{today}_b5_inputs_{hour}.json shows "
        f"the hourly store newest bar {out['hourly_newest']} "
        f"({out['hourly_newest_age_days']} days behind), "
        f"{out['hourly_stale_files']} of {out['hourly_files']} files past the "
        f"two-day freshness limit and {out['hourly_fresh_files']} current. "
        f"signals/book.csv has {out['legs_rows']} rows and no book-legs file "
        f"exists, so there is no leg list to time. No registered daemon "
        f"refreshes the hourly store. A timing rule built from stale bars "
        f"would not be a result, and a research run does not pull. Blocked "
        f"on the hourly store. {ANCHOR}"
    )
    text = open(BACKLOG).read()
    if note.strip() in text:
        print("note already present")
        return
    line = next(ln for ln in text.splitlines() if ln.startswith("- B5. "))
    at = line.rfind(ANCHOR)
    if at < 0:
        raise SystemExit("anchor missing from the B5 line")
    updated = line[:at] + ANCHOR + note + line[at + len(ANCHOR):]
    open(BACKLOG, "w").write(text.replace(line, updated, 1))
    print("noted")


if __name__ == "__main__":
    main()
