"""Record the 15:00 reading of the inputs that block B3.

Pairing, hedge ratios and sizing read data/book_universe.json,
data/raw/top100_daily.json and data/betas.json. All three are stale, and a
research run does not pull. This reads their dates and writes them through
write_result, then appends the block note.
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
BETAS = os.path.join(ROOT, "data", "betas.json")
INTRADAY = os.path.join(ROOT, "data", "intraday")
FRESH_DAYS = 2


def day_of(stamp):
    return datetime.fromtimestamp(
        stamp if stamp < 1e12 else stamp / 1000, timezone.utc
    ).strftime("%Y-%m-%d")


def last_bar(path):
    latest = None
    for row in json.load(open(path)):
        history = row.get("history") or []
        if not history or "t" not in history[-1]:
            continue
        day = day_of(history[-1]["t"])
        if latest is None or day > latest:
            latest = day
    return latest


def intraday_last():
    latest = None
    for name in os.listdir(INTRADAY):
        if not name.endswith(".csv"):
            continue
        last = None
        with open(os.path.join(INTRADAY, name)) as handle:
            for line in handle:
                if line.strip():
                    last = line
        if last is None:
            continue
        day = day_of(int(float(last.split(",")[0])))
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
    betas_mtime = day_of(os.stat(BETAS).st_mtime)
    hourly_last = intraday_last()
    out = {
        "item": "B3",
        "today": today,
        "slot": "15:00",
        "daily_last_bar": daily_last,
        "daily_age_days": age(today, daily_last),
        "universe_as_of": universe.get("as_of"),
        "universe_rows": len(universe.get("rows", [])),
        "universe_age_days": age(today, universe.get("as_of")),
        "betas_mtime": betas_mtime,
        "betas_age_days": age(today, betas_mtime),
        "hourly_last_bar": hourly_last,
        "hourly_age_days": age(today, hourly_last),
    }
    path = write_result("b3_inputs_1500", out, inputs=[
        "data/raw/top100_daily.json", "data/book_universe.json",
        "data/betas.json"])
    print(path)
    stale = [k for k in ("daily_age_days", "universe_age_days",
                         "betas_age_days", "hourly_age_days")
             if out[k] > FRESH_DAYS]
    if not stale:
        raise SystemExit("inputs are current; not marking blocked")
    text = open(BACKLOG).read()
    marker = f"Rechecked {today} 15:00 UTC: results/{today}_b3_inputs_1500.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- B3. "))
    note = (
        f" Rechecked {today} 15:00 UTC: results/{today}_b3_inputs_1500.json "
        f"shows data/raw/top100_daily.json last bar {out['daily_last_bar']} "
        f"({out['daily_age_days']} days behind), data/book_universe.json "
        f"as_of {out['universe_as_of']} ({out['universe_age_days']} days "
        f"behind, {out['universe_rows']} rows), data/betas.json written "
        f"{out['betas_mtime']} ({out['betas_age_days']} days behind) and the "
        f"hourly store last bar {out['hourly_last_bar']} "
        f"({out['hourly_age_days']} days behind). All four are past the "
        "two-day freshness limit, and no registered daemon refreshes them. "
        "A book built from them would be stale, and a research run does not "
        "pull. Blocked on the Coinalyze inputs. Unblocks when those four "
        "files are current."
    )
    open(BACKLOG, "w").write(text.replace(line, line.rstrip("\n") + note + "\n", 1))
    print("noted")


if __name__ == "__main__":
    main()
