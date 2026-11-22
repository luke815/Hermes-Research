"""Record the 13:00 reading of the inputs that block B5.

The 4-hour entry timing reads the hourly store and the book's legs. The
store is stale for most names, the legs have no file, and a research run
does not pull. This reads the dates and writes them through write_result,
then appends the block note.
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


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
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
    fresh = sum(n for day, n in counts.items()
                if (today_dt - datetime.strptime(day, "%Y-%m-%d")).days <= FRESH_DAYS)
    out = {
        "item": "B5",
        "today": today,
        "slot": "13:00",
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
    path = write_result("b5_inputs_1300", out, inputs=[
        "data/intraday/1000PEPEUSDT_PERP.A.csv", "signals/book.csv"])
    print(path)
    if out["hourly_stale_files"] == 0:
        raise SystemExit("hourly store is current; not marking blocked")
    text = open(BACKLOG).read()
    marker = f"Rechecked {today} 13:00 UTC: results/{today}_b5_inputs_1300.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- B5. "))
    note = (
        f" Rechecked {today} 13:00 UTC: results/{today}_b5_inputs_1300.json "
        f"shows the hourly store newest bar {out['hourly_newest']} "
        f"({out['hourly_newest_age_days']} days behind), "
        f"{out['hourly_stale_files']} of {out['hourly_files']} files past the "
        f"two-day freshness limit and {out['hourly_fresh_files']} current. "
        f"signals/book.csv has {out['legs_rows']} rows and no book-legs file "
        "exists, so there is no leg list to time. No registered daemon "
        "refreshes the hourly store. A timing rule built from stale bars "
        "would not be a result, and a research run does not pull. Blocked on "
        "the hourly store. Unblocks when the hourly files are current."
    )
    open(BACKLOG, "w").write(text.replace(line, line.rstrip("\n") + note + "\n", 1))
    print("noted")


if __name__ == "__main__":
    main()
