"""One counter for the sweep, read by the daemon and the digest.

The daemon used to write ops/sweep_status itself, and the digest counted cells
from a different file, so the two numbers never matched. Both now read
results/sweeps/counter.json, which this module writes from the scored rows and
the testable list.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COUNTER = os.path.join(ROOT, "results", "sweeps", "counter.json")
STATUS = os.path.join(ROOT, "ops", "sweep_status")


def write_counter(scored, testable):
    """Record scored against testable. The caller writes its own status line."""
    payload = {"scored": int(scored), "testable": int(testable),
               "file": os.path.relpath(COUNTER, ROOT)}
    os.makedirs(os.path.dirname(COUNTER), exist_ok=True)
    tmp = COUNTER + ".tmp"
    open(tmp, "w").write(json.dumps(payload))
    os.replace(tmp, COUNTER)
    return payload


def read_counter():
    """The counter both readers cite. Missing file is an empty count, not a guess."""
    if not os.path.exists(COUNTER):
        return {"scored": None, "testable": None, "file": os.path.relpath(COUNTER, ROOT)}
    return json.load(open(COUNTER))
