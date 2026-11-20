"""One counter for the sweep, read by the daemon, the digest and the status line.

The daemon used to write ops/sweep_status itself, and the digest counted cells
from a different file, so the two numbers never matched. Both now read
results/sweeps/counter.json, which this module writes from the scored rows.

The count is every distinct cell id saved under results/sweeps since the last
admission, across every scoring path. Counting only the vectorized files hides
the single-name sweep, and the deflated bar then rests on a number the
confirmations do not.
"""

import csv
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COUNTER = os.path.join(ROOT, "results", "sweeps", "counter.json")
STATUS = os.path.join(ROOT, "ops", "sweep_status")
SWEEPS = os.path.join(ROOT, "results", "sweeps")
SPACE = os.path.join(ROOT, "results", "sweeps", "space.json")

# The last admission was the costs table on 2026-10-31 (research/log.md).
# Every scored cell since that date counts.
LAST_ADMISSION = "2026-10-31"


def _cited(path):
    """The path the digest and the status line print, relative to the repo.

    The counter lives in results/sweeps, three levels under the repo root, so
    the cited path keeps the results/ prefix. A test that points COUNTER at a
    temp file gets that file's own name instead.
    """
    return os.path.relpath(path, os.path.dirname(os.path.dirname(os.path.dirname(path))))


def scored_cell_ids(sweeps_dir=None, since=LAST_ADMISSION):
    """Distinct cell ids written by any scorer on or after the last admission.

    A file dated before the cutoff is a record of an earlier scorer and is not
    counted. A file with no id column is not a sweep result and is skipped.
    """
    directory = sweeps_dir or SWEEPS
    ids = set()
    files = []
    for path in sorted(glob.glob(os.path.join(directory, "*.csv"))):
        name = os.path.basename(path)
        if name[:10] < since:
            continue
        files.append(os.path.relpath(path, ROOT))
        with open(path, newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "id" not in reader.fieldnames:
                continue
            ids.update(row["id"] for row in reader if row.get("id"))
    return ids, files


def testable_count(space_path=None):
    """The enumerator's testable count, which is the denominator.

    A missing file is an absent count, not a guessed one. The two readers
    then print the same absence instead of two different numbers.
    """
    path = space_path or SPACE
    if not os.path.exists(path):
        return None
    with open(path) as handle:
        return json.load(handle).get("testable")


def write_counter(sweeps_dir=None, since=LAST_ADMISSION, space_path=None):
    """Recount from the files and record the number both readers cite."""
    ids, files = scored_cell_ids(sweeps_dir, since)
    payload = {
        "scored": len(ids),
        "testable": testable_count(space_path),
        "since": since,
        "files": files,
        "file": _cited(COUNTER),
    }
    os.makedirs(os.path.dirname(COUNTER), exist_ok=True)
    tmp = COUNTER + ".tmp"
    with open(tmp, "w") as handle:
        json.dump(payload, handle)
    os.replace(tmp, COUNTER)
    return payload


def read_counter():
    """The counter both readers cite. A missing file is an empty count, not a guess."""
    if not os.path.exists(COUNTER):
        return {"scored": None, "since": LAST_ADMISSION, "file": _cited(COUNTER)}
    with open(COUNTER) as handle:
        return json.load(handle)


def status_text(payload=None):
    """The one line the digest and ops/sweep_status both print."""
    payload = payload or read_counter()
    text = (f"cells scored {payload['scored']} of {payload.get('testable')} "
            f"testable since {payload.get('since')}, from {payload['file']}")
    return text
