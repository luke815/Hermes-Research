"""Record one recheck of the inputs that block B4.

The book backtest reads data/book_universe.json and
data/raw/top100_daily.json, and it runs through strategy.py. The slot is
today's UTC hour, read from the clock. This reads their dates and writes
them through write_result, then appends the block note. It does not pull.

Usage: python3 scripts/record_b4_reading.py
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
FRESH_DAYS = 2
ANCHOR = "Unblocks when those two files are current."


def last_bar(path):
    latest = None
    for row in json.load(open(path)):
        history = row.get("history") or []
        if not history or "t" not in history[-1]:
            continue
        stamp = history[-1]["t"]
        day = datetime.fromtimestamp(
            stamp if stamp < 1e12 else stamp / 1000, timezone.utc
        ).strftime("%Y-%m-%d")
        if latest is None or day > latest:
            latest = day
    return latest


def age(today, day):
    return (datetime.strptime(today, "%Y-%m-%d")
            - datetime.strptime(day, "%Y-%m-%d")).days


def main():
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    hour = now.strftime("%H00")
    slot = now.strftime("%Y-%m-%d %H:00")
    daily_last = last_bar(DAILY)
    universe = json.load(open(UNIVERSE))
    strategy = os.path.exists(os.path.join(ROOT, "regime_tester", "strategy.py"))
    out = {
        "item": "B4",
        "slot": slot,
        "daily_last_bar": daily_last,
        "daily_age_days": age(today, daily_last),
        "universe_as_of": universe.get("as_of"),
        "universe_rows": len(universe.get("rows", [])),
        "universe_age_days": age(today, universe.get("as_of")),
        "strategy_module_present": strategy,
    }
    path = write_result(f"b4_inputs_{hour}", out, inputs=[
        "data/raw/top100_daily.json", "data/book_universe.json"])
    print(path)
    if out["daily_age_days"] <= FRESH_DAYS and out["universe_age_days"] <= FRESH_DAYS:
        raise SystemExit("inputs are current; not marking blocked")
    note = (
        f" Rechecked {slot} UTC: results/{today}_b4_inputs_{hour}.json shows "
        f"data/raw/top100_daily.json last bar {out['daily_last_bar']} "
        f"({out['daily_age_days']} days behind) and data/book_universe.json "
        f"as_of {out['universe_as_of']} ({out['universe_age_days']} days "
        f"behind, {out['universe_rows']} rows). Both are past the two-day "
        f"freshness limit, and no registered daemon refreshes them. "
        f"regime_tester/strategy.py is "
        f"{'present' if strategy else 'absent'}. A backtest built from stale "
        f"inputs would not be a result, and a research run does not pull. "
        f"Blocked on the Coinalyze inputs. {ANCHOR}"
    )
    text = open(BACKLOG).read()
    if note.strip() in text:
        print("note already present")
        return
    line = next(ln for ln in text.splitlines() if ln.startswith("- B4. "))
    at = line.rfind(ANCHOR)
    if at < 0:
        raise SystemExit("anchor missing from the B4 line")
    updated = line[:at] + ANCHOR + note + line[at + len(ANCHOR):]
    open(BACKLOG, "w").write(text.replace(line, updated, 1))
    print("noted")


if __name__ == "__main__":
    main()
