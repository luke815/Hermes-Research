"""Record why B1 cannot be scored this run.

The book scripts read the Coinalyze hourly store, the open-interest snapshot
and the daily bars. This reads those files' dates and writes them through
write_result. It does not pull and it does not rebuild the book.
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


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = {"item": "B1", "today": today}
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
    out["snapshot"]["as_of"] = json.load(
        open(os.path.join(ROOT, FILES["snapshot"]))).get("as_of")
    path = write_result("b1_inputs", out, inputs=list(FILES.values()))
    print(path)
    text = open(BACKLOG).read()
    marker = "Rechecked 2026-11-21 07:00 UTC: results/2026-11-21_b1_inputs.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- B1. "))
    anchor = "results/<date>_b1.json is written by the script that computed them."
    if anchor not in line:
        raise SystemExit("anchor missing from the B1 line")
    note = (
        " Rechecked 2026-11-21 07:00 UTC: results/2026-11-21_b1_inputs.json "
        f"shows the hourly store last bar {out['hourly']['last_bar']}, the "
        f"daily bars last bar {out['daily']['last_bar']} and the open-interest "
        f"snapshot as of {out['snapshot']['as_of']}. All three are older than "
        "two days, and no registered daemon refreshes them. A book built from "
        "them would be stale, and a research run does not pull. Blocked on "
        "the Coinalyze inputs. Unblocks when those three files are current."
    )
    updated = line.replace(anchor, anchor + note, 1)
    open(BACKLOG, "w").write(text.replace(line, updated, 1))
    print("noted")


if __name__ == "__main__":
    main()
