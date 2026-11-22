"""Record the 02:00 reading of the inputs that block B3.

Pairing, hedge ratios and sizing read data/book_universe.json,
data/raw/top100_daily.json, data/betas.json and the hourly store. A
research run does not pull. This reads their dates, counts how many
hourly files are past the freshness limit, and writes them through
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


def hourly_ages(today):
    today_dt = datetime.strptime(today, "%Y-%m-%d")
    ages = {}
    newest = None
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
        ages[name] = (today_dt - datetime.strptime(day, "%Y-%m-%d")).days
        if newest is None or day > newest:
            newest = day
    stale = sum(1 for age in ages.values() if age > FRESH_DAYS)
    return newest, len(ages), stale


def age(today, day):
    return (datetime.strptime(today, "%Y-%m-%d")
            - datetime.strptime(day, "%Y-%m-%d")).days


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    daily_last = last_bar(DAILY)
    universe = json.load(open(UNIVERSE))
    betas_mtime = day_of(os.stat(BETAS).st_mtime)
    hourly_last, hourly_files, hourly_stale = hourly_ages(today)
    out = {
        "item": "B3",
        "today": today,
        "slot": "02:00",
        "daily_last_bar": daily_last,
        "daily_age_days": age(today, daily_last),
        "universe_as_of": universe.get("as_of"),
        "universe_rows": len(universe.get("rows", [])),
        "universe_age_days": age(today, universe.get("as_of")),
        "betas_mtime": betas_mtime,
        "betas_age_days": age(today, betas_mtime),
        "hourly_last_bar": hourly_last,
        "hourly_age_days": age(today, hourly_last),
        "hourly_files": hourly_files,
        "hourly_stale_files": hourly_stale,
    }
    path = write_result("b3_inputs_0200", out, inputs=[
        "data/raw/top100_daily.json", "data/book_universe.json",
        "data/betas.json", "data/intraday"])
    print(path)
    stale = [name for name in (
        "daily_age_days", "universe_age_days", "betas_age_days")
        if out[name] > FRESH_DAYS]
    if not stale and hourly_stale == 0:
        raise SystemExit("inputs are current; not marking blocked")
    text = open(BACKLOG).read()
    marker = f"Rechecked {today} 02:00 UTC: results/{today}_b3_inputs_0200.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- B3. "))
    note = (
        f" Rechecked {today} 02:00 UTC: results/{today}_b3_inputs_0200.json "
        f"shows data/raw/top100_daily.json last bar {out['daily_last_bar']} "
        f"({out['daily_age_days']} days behind), data/book_universe.json "
        f"as_of {out['universe_as_of']} ({out['universe_age_days']} days "
        f"behind, {out['universe_rows']} rows) and data/betas.json written "
        f"{out['betas_mtime']} ({out['betas_age_days']} days behind). The "
        f"hourly store's newest bar is {out['hourly_last_bar']} "
        f"({out['hourly_age_days']} days behind) and "
        f"{out['hourly_stale_files']} of {out['hourly_files']} files are "
        f"past the two-day limit. No registered daemon refreshes the book "
        f"inputs. A pairing built from them would be stale, and a research "
        f"run does not pull. Blocked on the Coinalyze inputs. Unblocks when "
        f"the daily bars, the universe and the betas are current.")
    open(BACKLOG, "w").write(text.replace(line, line.rstrip("\n") + note + "\n", 1))
    print("noted")


if __name__ == "__main__":
    main()
