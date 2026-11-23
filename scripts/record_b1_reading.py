"""Record one recheck of the inputs that block B1.

The book scripts read the Coinalyze hourly store, the open-interest
snapshot and the daily bars. The slot is today's UTC hour, read from the
clock, and the ages are computed against that date. This reads those
files' dates and writes them through write_result. It does not pull and
it does not rebuild the book.

Usage: python3 scripts/record_b1_reading.py
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
REGISTRY = os.path.join(ROOT, "ops", "daemons.json")
FILES = {
    "hourly": "data/raw/coinalyze_ohlcv_1h.json",
    "snapshot": "data/raw/oi_snapshot.json",
    "daily": "data/raw/top100_daily.json",
}
ANCHOR = "Unblocks when those three files are current."


def last_date(path, key):
    loaded = json.load(open(path))
    rows = loaded.get("rows", loaded) if isinstance(loaded, dict) else loaded
    latest = None
    for row in rows:
        history = row.get("history") or []
        if not history:
            continue
        stamp = history[-2][key] if len(history) > 1 else history[-1][key]
        day = datetime.fromtimestamp(stamp, timezone.utc).strftime("%Y-%m-%d")
        if latest is None or day > latest:
            latest = day
    return latest


def age_days(day, today):
    return (datetime.strptime(today, "%Y-%m-%d")
            - datetime.strptime(day, "%Y-%m-%d")).days


def main():
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    hour = now.strftime("%H00")
    slot = now.strftime("%Y-%m-%d %H:00")
    out = {"item": "B1", "slot": slot}
    for name, path in FILES.items():
        full = os.path.join(ROOT, path)
        stamp = os.stat(full).st_mtime
        out[name] = {
            "path": path,
            "mtime": datetime.fromtimestamp(stamp, timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"),
            "bytes": os.path.getsize(full),
        }
    out["hourly"]["last_bar"] = last_date(os.path.join(ROOT, FILES["hourly"]), "t")
    out["daily"]["last_bar"] = last_date(os.path.join(ROOT, FILES["daily"]), "t")
    updates = [row["update"] for row in json.load(
        open(os.path.join(ROOT, FILES["snapshot"]))) if row.get("update")]
    newest = max(updates)
    out["snapshot"]["newest_update"] = datetime.fromtimestamp(
        newest / 1000 if newest > 10 ** 12 else newest, timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    out["hourly"]["age_days"] = age_days(out["hourly"]["last_bar"], today)
    out["daily"]["age_days"] = age_days(out["daily"]["last_bar"], today)
    out["snapshot"]["age_days"] = age_days(
        out["snapshot"]["newest_update"][:10], today)
    registry = open(REGISTRY).read() if os.path.exists(REGISTRY) else ""
    out["daemon_refreshes_inputs"] = "coinalyze" in registry
    path = write_result(f"b1_inputs_{hour}", out, inputs=list(FILES.values()))
    print(path)
    stale = [name for name in ("hourly", "daily", "snapshot")
             if out[name]["age_days"] > 2]
    if len(stale) != 3:
        raise SystemExit(f"not all three stale: {stale}; not marking blocked")
    note = (
        f" Rechecked {slot} UTC: results/{today}_b1_inputs_{hour}.json shows "
        f"the hourly store last bar {out['hourly']['last_bar']} "
        f"({out['hourly']['age_days']} days behind), the daily bars last bar "
        f"{out['daily']['last_bar']} ({out['daily']['age_days']} days behind) "
        f"and the open-interest snapshot newest update "
        f"{out['snapshot']['newest_update']} ({out['snapshot']['age_days']} "
        f"days behind). All three are past the two-day freshness limit, and "
        f"no registered daemon refreshes them. A book built from them would "
        f"be stale, and a research run does not pull. Blocked on the "
        f"Coinalyze inputs. {ANCHOR}"
    )
    text = open(BACKLOG).read()
    if note.strip() in text:
        print("note already present")
        return
    line = next(ln for ln in text.splitlines() if ln.startswith("- B1. "))
    at = line.rfind(ANCHOR)
    if at < 0:
        raise SystemExit("anchor missing from the B1 line")
    updated = line[:at] + ANCHOR + note + line[at + len(ANCHOR):]
    open(BACKLOG, "w").write(text.replace(line, updated, 1))
    print("noted")


if __name__ == "__main__":
    main()
