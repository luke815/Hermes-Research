"""Record the 13:00 reading of the inputs that block B2.

The book reads the daily bars and the book universe. This reads both dates
and writes the ages. It does not pull and it does not rebuild the book.
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
DAILY = os.path.join(ROOT, "data", "raw", "top100_daily.json")
BOOK = os.path.join(ROOT, "data", "book_universe.json")
REGISTRY = os.path.join(ROOT, "ops", "daemons.json")
SLOT = "2026-11-22 13:00"
ANCHOR = "Unblocks when those two files are current."


def age_days(day, today):
    return (datetime.strptime(today, "%Y-%m-%d")
            - datetime.strptime(day[:10], "%Y-%m-%d")).days


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    daily = json.load(open(DAILY))
    daily_last = None
    for row in daily:
        history = row.get("history") or []
        if not history or history[-1].get("t") is None:
            continue
        day = datetime.fromtimestamp(
            history[-1]["t"], timezone.utc).strftime("%Y-%m-%d")
        if daily_last is None or day > daily_last:
            daily_last = day
    book = json.load(open(BOOK))
    registry = sorted(json.load(open(REGISTRY)))
    out = {
        "item": "B2",
        "slot": SLOT,
        "today": today,
        "daily_last_bar": daily_last,
        "daily_age_days": age_days(daily_last, today),
        "book_as_of": book.get("as_of"),
        "book_age_days": age_days(book.get("as_of"), today),
        "book_rows": len(book.get("rows", [])),
        "registered_daemons": registry,
        "coinalyze_daemon": None,
        "blocked": "Coinalyze inputs are past the two-day freshness limit",
        "unblocks": "those two files are current",
    }
    path = write_result("b2_inputs_1300", out, inputs=[
        "data/raw/top100_daily.json", "data/book_universe.json",
        "ops/daemons.json"])
    print(path)
    if min(out["daily_age_days"], out["book_age_days"]) <= 2:
        raise SystemExit("an input is current; not marking blocked")
    note = (
        f" Rechecked {SLOT} UTC: results/2026-11-22_b2_inputs_1300.json shows "
        f"data/raw/top100_daily.json last bar {daily_last} "
        f"({out['daily_age_days']} days behind) and data/book_universe.json "
        f"as_of {book.get('as_of')} ({out['book_age_days']} days behind, "
        f"{out['book_rows']} rows). Both are past the two-day freshness "
        f"limit, and no registered daemon refreshes them. A book built from "
        f"them would be stale, and a research run does not pull. Unchanged "
        f"since the 09:00 note. Blocked on the Coinalyze inputs. {ANCHOR}"
    )
    text = open(BACKLOG).read()
    if note.strip() in text:
        print("note already present")
        return
    line = next(ln for ln in text.splitlines() if ln.startswith("- B2. "))
    if ANCHOR not in line:
        raise SystemExit("anchor missing")
    updated = line.replace(ANCHOR, ANCHOR + note, 1)
    open(BACKLOG, "w").write(text.replace(line, updated, 1))
    print("noted")


if __name__ == "__main__":
    main()
