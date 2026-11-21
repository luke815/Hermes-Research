"""Record why B1 cannot be scored at the 17:00 run.

The book scripts read the Coinalyze hourly store, the open-interest
snapshot and the daily bars. This reads those files' dates, computes the
age against today, and writes them through write_result. It does not pull
and it does not rebuild the book.
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
FRESH_DAYS = 2


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


def refresher():
    """A registered daemon whose command names one of the three files."""
    try:
        registry = json.load(open(REGISTRY))
    except (OSError, json.JSONDecodeError):
        return []
    found = []
    blobs = registry.values() if isinstance(registry, dict) else registry
    for entry in blobs:
        text = json.dumps(entry)
        if any(name in text for name in (
                "coinalyze_ohlcv_1h", "oi_snapshot", "top100_daily")):
            found.append(entry.get("name") if isinstance(entry, dict) else str(entry))
    return found


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = {"item": "B1", "today": today, "slot": "17:00",
           "fresh_limit_days": FRESH_DAYS}
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
    for name, key in (("hourly", "last_bar"), ("daily", "last_bar"),
                      ("snapshot", "newest_update")):
        day = out[name][key][:10]
        out[name]["age_days"] = age_days(day, today)
        out[name]["stale"] = out[name]["age_days"] > FRESH_DAYS
    owners = refresher()
    out["refreshing_daemons"] = owners
    path = write_result("b1_inputs_1700", out, inputs=list(FILES.values()))
    print(path)
    stale = [name for name in FILES if out[name]["stale"]]
    if not stale or owners:
        raise SystemExit("the block changed; not marking blocked")
    text = open(BACKLOG).read()
    marker = f"Rechecked {today} 17:00 UTC: results/{today}_b1_inputs_1700.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- B1. "))
    anchor = "Unblocks when those three files are current."
    if line.count(anchor) < 1:
        raise SystemExit("anchor missing from the B1 line")
    note = (
        f" Rechecked {today} 17:00 UTC: results/{today}_b1_inputs_1700.json "
        f"shows the hourly store last bar {out['hourly']['last_bar']} "
        f"({out['hourly']['age_days']} days behind), the daily bars last bar "
        f"{out['daily']['last_bar']} ({out['daily']['age_days']} days behind) "
        f"and the open-interest snapshot newest update "
        f"{out['snapshot']['newest_update']} "
        f"({out['snapshot']['age_days']} days behind). All three are past the "
        f"two-day freshness limit, and no registered daemon refreshes them. "
        f"A book built from them would be stale, and a research run does not "
        f"pull. Blocked on the Coinalyze inputs. {anchor}")
    # replace the last anchor, so the new reading is the last one on the line
    head, _, tail = line.rpartition(anchor)
    updated = head + note
    if tail:
        raise SystemExit("anchor was not at the end of the B1 line")
    open(BACKLOG, "w").write(text.replace(line, updated, 1))
    print("noted")


if __name__ == "__main__":
    main()
