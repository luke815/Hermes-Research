"""The record of health.rs_stale, one row per reading.

A5 needs the flag false for a full day. The live daemon force-pushes its
payload, so the previous reading is gone, and a single snapshot cannot show a
span. This log keeps every reading and answers how long the flag has stayed
false without a gap. A gap is not a continuation: the flag may have flipped in
the time nobody looked.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "ops", "rs_stale_log.jsonl")


def _rows(path):
    """Readings from the log. A blank line or one that is not JSON is skipped:
    the file has been padded with NUL bytes, and one of those must not stop
    the live daemon."""
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path) as handle:
        for line in handle:
            line = line.strip("\x00 \t\r\n")
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def append(path, ts, rs_stale, rs_age_sec):
    """Append one reading. A repeat of the last timestamp is ignored, so a
    re-read of the same payload does not count as a second observation."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    last = _rows(path)[-1]["ts"] if _rows(path) else None
    if last == ts:
        return False
    with open(path, "a") as handle:
        handle.write(json.dumps({"ts": ts, "rs_stale": bool(rs_stale),
                                  "rs_age_sec": rs_age_sec}) + "\n")
    return True


def read(path):
    return _rows(path)


def false_span_hours(rows):
    """Hours the flag has been false, ending at the newest reading.

    The span starts at the first reading after the last true one, and a gap of
    more than six hours between readings ends it: that time was not observed.
    None when the newest reading is true or no reading exists.
    """
    if not rows or rows[-1]["rs_stale"]:
        return None
    start = 0
    for i, row in enumerate(rows):
        if row["rs_stale"]:
            start = i + 1
    run = rows[start:]
    for earlier, later in zip(run, run[1:]):
        if _epoch(later["ts"]) - _epoch(earlier["ts"]) > 6 * 3600:
            start_ts = later["ts"]
            run = [r for r in run if r["ts"] >= start_ts]
    if len(run) < 2:
        return 0.0
    return round((_epoch(run[-1]["ts"]) - _epoch(run[0]["ts"])) / 3600, 2)


def _epoch(ts):
    from datetime import datetime
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").timestamp()
