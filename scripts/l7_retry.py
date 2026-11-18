"""L7: count the 400 and 404 files the puller will retry.

Reads the perpetual store. A file with an error and no error_on is the old
mark-forever form, so it is pending now. A file whose error_on is 7 days or
more before today is pending too. The newest bar is read from one current
file, not from every history: the error files are the only ones this item
changes, and they carry no bars.
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import laevitas_pull as pull  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

STORE = pull.STORE


def scan(store, today):
    undated = 0
    dated = 0
    due = 0
    files = 0
    newest = None
    newest_name = None
    for name in sorted(os.listdir(store)):
        if not name.endswith(".json"):
            continue
        files += 1
        path = os.path.join(store, name)
        with open(path) as handle:
            head = handle.read(200)
            if '"error"' not in head:
                if newest is None:
                    body = json.loads(head + handle.read())
                    dates = [i.get("date") for i in body.get("items", [])
                             if isinstance(i, dict) and i.get("date")]
                    if dates:
                        newest = max(dates)
                        newest_name = name
                continue
            body = json.loads(head + handle.read())
        if not body.get("error"):
            continue
        dated += 1
        seen = body.get("error_on")
        if not seen:
            undated += 1
            due += 1
            continue
        gap = (datetime.strptime(today, "%Y-%m-%d").date()
               - datetime.strptime(seen, "%Y-%m-%d").date()).days
        if gap >= pull.RETRY_AFTER_DAYS:
            due += 1
    newest_bar = None
    if newest is not None:
        newest_bar = datetime.fromtimestamp(newest / 1000, timezone.utc).strftime("%Y-%m-%d")
    return {
        "files": files,
        "error_files": dated,
        "error_files_without_date": undated,
        "due_for_retry": due,
        "newest_bar": newest_bar,
        "newest_file": newest_name,
        "retry_after_days": pull.RETRY_AFTER_DAYS,
    }


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    payload = scan(STORE, today)
    payload["today"] = today
    path = write_result("l7_retry", payload, inputs=["data/laevitas/perpetuals"])
    print(path)
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
