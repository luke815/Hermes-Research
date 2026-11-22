"""Record the 02:00 reading of the inputs that block B2.

The book scripts read data/book_universe.json and data/raw/top100_daily.json.
Both are stale, and a research run does not pull. This reads their dates and
writes them through write_result, then appends the block note.
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
UNIVERSE = os.path.join(ROOT, "data", "book_universe.json")


def last_bar(path):
    loaded = json.load(open(path))
    latest = None
    for row in loaded:
        history = row.get("history") or []
        if not history or "t" not in history[-1]:
            continue
        stamp = history[-1]["t"]
        day = datetime.fromtimestamp(
            stamp if stamp < 1e12 else stamp / 1000,
            timezone.utc).strftime("%Y-%m-%d")
        if latest is None or day > latest:
            latest = day
    return latest


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    daily_last = last_bar(DAILY)
    universe = json.load(open(UNIVERSE))
    out = {
        "item": "B2",
        "today": today,
        "slot": "02:00",
        "daily_last_bar": daily_last,
        "daily_age_days": (
            datetime.strptime(today, "%Y-%m-%d")
            - datetime.strptime(daily_last, "%Y-%m-%d")).days,
        "universe_as_of": universe.get("as_of"),
        "universe_rows": len(universe.get("rows", [])),
        "universe_age_days": (
            datetime.strptime(today, "%Y-%m-%d")
            - datetime.strptime(universe.get("as_of"), "%Y-%m-%d")).days,
    }
    path = write_result("b2_inputs_0200", out, inputs=[
        "data/raw/top100_daily.json", "data/book_universe.json"])
    print(path)
    if out["daily_age_days"] <= 2 and out["universe_age_days"] <= 2:
        raise SystemExit("inputs are current; not marking blocked")
    text = open(BACKLOG).read()
    marker = f"Rechecked {today} 02:00 UTC: results/{today}_b2_inputs_0200.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- B2. "))
    note = (
        f" Rechecked {today} 02:00 UTC: results/{today}_b2_inputs_0200.json "
        f"shows data/raw/top100_daily.json last bar {out['daily_last_bar']} "
        f"({out['daily_age_days']} days behind) and data/book_universe.json "
        f"as_of {out['universe_as_of']} ({out['universe_age_days']} days "
        f"behind, {out['universe_rows']} rows). Both are past the two-day "
        "freshness limit, and no registered daemon refreshes them. A book "
        "built from them would be stale, and a research run does not pull. "
        "Blocked on the Coinalyze inputs. Unblocks when those two files are "
        "current."
    )
    open(BACKLOG, "w").write(text.replace(line, line.rstrip("\n") + note + "\n", 1))
    print("noted")


if __name__ == "__main__":
    main()
