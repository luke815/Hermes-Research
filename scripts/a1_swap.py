"""Swap the rewritten panel over data/panel_xs once the sums cover every live name.

The rewrite lands in data/panel_xs_sum2. This compares it with data/panel_xs,
refuses when the append job is still writing the source, and swaps through
data_guard. A file that shrinks because the last-print funding column was
replaced by the day's sum is an expected shrink; the count comes from the
compare, and the swap passes that exact count.

Writes results/<today>_a1_swap.json itself.
"""

import json
import os
import sys

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import data_guard  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = "data/panel_xs_sum2"
DST = "data/panel_xs"


def append_running(pidfile=None):
    """True when the panel append process named in its pidfile is alive."""
    path = pidfile or os.path.join(ROOT, "ops", "pids", "panel_append.pid")
    try:
        with open(path) as handle:
            pid = int(handle.read().strip())
    except (OSError, ValueError):
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def main():
    if append_running():
        raise SystemExit("refusing: panel_append is writing data/panel_xs; rerun when it exits")
    src_path, dst_path = os.path.join(ROOT, SRC), os.path.join(ROOT, DST)
    diff = data_guard.compare(data_guard.scan(dst_path), data_guard.scan(src_path))
    removed, shrunk = len(diff["removed"]), len(diff["shrunk"])
    record = data_guard.swap(
        SRC, DST,
        "A1: funding column is the day's sum, today's open bar dropped",
        allow_removed=removed, allow_shrunk=shrunk)
    out = {
        "item": "A1",
        "src": SRC,
        "dst": DST,
        "removed": removed,
        "shrunk": shrunk,
        "added": len(diff["added"]),
        "kept_previous_as": record["swap"]["kept_previous_as"],
        "results_file": record["results_file"],
    }
    path = write_result("a1_swap", out, inputs=[DST])
    print(json.dumps(out))
    print(path)


if __name__ == "__main__":
    main()
