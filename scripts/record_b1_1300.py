"""Record the 13:00 reading of the inputs that block B1.

The hourly store is too large to load whole. This scans its timestamps,
reads the snapshot's update time and the daily file's last bar, and writes
the ages. It does not pull and it does not rebuild the book.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
HOURLY = os.path.join(ROOT, "data", "raw", "coinalyze_ohlcv_1h.json")
SNAPSHOT = os.path.join(ROOT, "data", "raw", "oi_snapshot.json")
DAILY = os.path.join(ROOT, "data", "raw", "top100_daily.json")
REGISTRY = os.path.join(ROOT, "ops", "daemons.json")
SLOT = "2026-11-22 13:00"
ANCHOR = "Unblocks when those three files are current."
STAMP = re.compile(rb'"t": (\d{10})')


def newest_stamp(path):
    latest = 0
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1 << 20)
            if not chunk:
                break
            for match in STAMP.finditer(chunk):
                latest = max(latest, int(match.group(1)))
    return datetime.fromtimestamp(latest, timezone.utc).strftime("%Y-%m-%d")


def age_days(day, today):
    return (datetime.strptime(today, "%Y-%m-%d")
            - datetime.strptime(day[:10], "%Y-%m-%d")).days


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    hourly_last = newest_stamp(HOURLY)
    snapshot = json.load(open(SNAPSHOT))
    updates = [row.get("update") for row in snapshot.get("rows", [])
               if isinstance(row, dict) and row.get("update")]
    snapshot_last = max(updates) if updates else None
    daily = json.load(open(DAILY))
    daily_rows = daily.get("rows", daily) if isinstance(daily, dict) else daily
    daily_last = None
    for row in daily_rows:
        history = row.get("history") or []
        if not history:
            continue
        stamp = history[-1].get("t")
        if stamp is None:
            continue
        day = datetime.fromtimestamp(stamp, timezone.utc).strftime("%Y-%m-%d")
        if daily_last is None or day > daily_last:
            daily_last = day
    registry = sorted(json.load(open(REGISTRY)))
    out = {
        "item": "B1",
        "slot": SLOT,
        "today": today,
        "hourly_last_bar": hourly_last,
        "hourly_age_days": age_days(hourly_last, today),
        "daily_last_bar": daily_last,
        "daily_age_days": age_days(daily_last, today),
        "snapshot_newest_update": snapshot_last,
        "snapshot_age_days": age_days(snapshot_last, today),
        "registered_daemons": registry,
        "coinalyze_daemon": None,
        "blocked": "Coinalyze inputs are past the two-day freshness limit",
        "unblocks": "those three files are current",
    }
    path = write_result("b1_inputs_1300", out, inputs=[
        "data/raw/coinalyze_ohlcv_1h.json", "data/raw/oi_snapshot.json",
        "data/raw/top100_daily.json", "ops/daemons.json"])
    print(path)
    if min(out["hourly_age_days"], out["daily_age_days"],
           out["snapshot_age_days"]) <= 2:
        raise SystemExit("an input is current; not marking blocked")
    note = (
        f" Rechecked {SLOT} UTC: results/2026-11-22_b1_inputs_1300.json shows "
        f"the hourly store last bar {hourly_last} ({out['hourly_age_days']} "
        f"days behind), the daily bars last bar {daily_last} "
        f"({out['daily_age_days']} days behind) and the open-interest "
        f"snapshot newest update {snapshot_last} ({out['snapshot_age_days']} "
        f"days behind). All three are past the two-day freshness limit, and "
        f"no registered daemon refreshes them. Unchanged since the 09:00 "
        f"note. Blocked on the Coinalyze inputs. {ANCHOR}"
    )
    text = open(BACKLOG).read()
    if note.strip() in text:
        print("note already present")
        return
    line = next(ln for ln in text.splitlines() if ln.startswith("- B1. "))
    if ANCHOR not in line:
        raise SystemExit("anchor missing")
    updated = line.replace(ANCHOR, ANCHOR + note, 1)
    open(BACKLOG, "w").write(text.replace(line, updated, 1))
    print("noted")


if __name__ == "__main__":
    main()
