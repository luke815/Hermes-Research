"""Record the 19:00 reading of the inputs that block B1.

The book scripts read the Coinalyze hourly store, the open-interest
snapshot and the daily bars. This reads those files' dates, computes how
many days each lags today, and writes them through write_result. It does
not pull and it does not rebuild the book.
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
FILES = {
    "hourly": "data/raw/coinalyze_ohlcv_1h.json",
    "snapshot": "data/raw/oi_snapshot.json",
    "daily": "data/raw/top100_daily.json",
}


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
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = {"item": "B1", "today": today, "slot": "19:00"}
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
    path = write_result("b1_inputs_1900", out, inputs=list(FILES.values()))
    print(path)
    stale = [name for name in ("hourly", "daily", "snapshot")
             if out[name]["age_days"] > 2]
    if len(stale) != 3:
        raise SystemExit(f"not all three stale: {stale}; not marking blocked")
    text = open(BACKLOG).read()
    marker = f"Rechecked {today} 19:00 UTC: results/{today}_b1_inputs_1900.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- B1. "))
    anchor = "Unblocks when those three files are current."
    at = line.rfind(anchor)
    if at < 0:
        raise SystemExit("anchor missing from the B1 line")
    note = (
        f" Rechecked {today} 19:00 UTC: results/{today}_b1_inputs_1900.json "
        f"shows the hourly store last bar {out['hourly']['last_bar']} "
        f"({out['hourly']['age_days']} days behind), the daily bars last bar "
        f"{out['daily']['last_bar']} ({out['daily']['age_days']} days behind) "
        f"and the open-interest snapshot newest update "
        f"{out['snapshot']['newest_update']} ({out['snapshot']['age_days']} "
        "days behind). All three are past the two-day freshness limit, and no "
        "registered daemon refreshes them. A book built from them would be "
        "stale, and a research run does not pull. Blocked on the Coinalyze "
        "inputs. Unblocks when those three files are current."
    )
    updated = line[:at] + anchor + note + line[at + len(anchor):]
    open(BACKLOG, "w").write(text.replace(line, updated, 1))
    print("noted")


if __name__ == "__main__":
    main()
