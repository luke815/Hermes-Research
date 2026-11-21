"""Record the 19:00 reading of the inputs that block B4.

The book backtest reads data/book_universe.json and
data/raw/top100_daily.json, and it runs through strategy.py, which is not
in the tree. Both inputs are stale and a research run does not pull. This
reads their dates and writes them through write_result, then appends the
block note.
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
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    daily_last = last_bar(DAILY)
    universe = json.load(open(UNIVERSE))
    strategy = os.path.exists(os.path.join(ROOT, "regime_tester", "strategy.py"))
    out = {
        "item": "B4",
        "today": today,
        "slot": "19:00",
        "daily_last_bar": daily_last,
        "daily_age_days": age(today, daily_last),
        "universe_as_of": universe.get("as_of"),
        "universe_rows": len(universe.get("rows", [])),
        "universe_age_days": age(today, universe.get("as_of")),
        "strategy_module_present": strategy,
    }
    path = write_result("b4_inputs_1900", out, inputs=[
        "data/raw/top100_daily.json", "data/book_universe.json"])
    print(path)
    if out["daily_age_days"] <= FRESH_DAYS and out["universe_age_days"] <= FRESH_DAYS:
        raise SystemExit("inputs are current; not marking blocked")
    text = open(BACKLOG).read()
    marker = f"Rechecked {today} 19:00 UTC: results/{today}_b4_inputs_1900.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- B4. "))
    note = (
        f" Rechecked {today} 19:00 UTC: results/{today}_b4_inputs_1900.json "
        f"shows data/raw/top100_daily.json last bar {out['daily_last_bar']} "
        f"({out['daily_age_days']} days behind) and data/book_universe.json "
        f"as_of {out['universe_as_of']} ({out['universe_age_days']} days "
        f"behind, {out['universe_rows']} rows). Both are past the two-day "
        "freshness limit, and no registered daemon refreshes them. "
        f"regime_tester/strategy.py is "
        f"{'present' if strategy else 'absent'}. A backtest built from stale "
        "inputs would not be a result, and a research run does not pull. "
        "Blocked on the Coinalyze inputs. Unblocks when those two files are "
        "current."
    )
    open(BACKLOG, "w").write(text.replace(line, line.rstrip("\n") + note + "\n", 1))
    print("noted")


if __name__ == "__main__":
    main()
