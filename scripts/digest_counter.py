"""The daily digest's counter line, read from the sweep's counter file.

Prints the scored count and the file it came from, so the digest cites the
same file and number as ops/sweep_status. The digest job's status line reads
this script's output rather than counting cells itself.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.counter import read_counter, status_text  # noqa: E402


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def line():
    return status_text(read_counter())


def top_item_line():
    """The top backlog item and the runs it has been there, from the health log.

    The digest ends with this line. It is read from ops/health.log, which the
    health check appends every run, so the digest and the health check cite
    the same item and the same count.
    """
    log = os.path.join(ROOT_DIR, "ops", "health.log")
    last = ""
    try:
        for row in open(log):
            if "stall_check item=" in row:
                last = row.strip()
    except OSError:
        return "top item unknown, health check has not run"
    if not last:
        return "top item unknown, health check has not run"
    item = last.split("item=", 1)[1].split(" ", 1)[0]
    runs = last.split("runs=", 1)[1].split(" ", 1)[0]
    return f"top backlog item {item}, {runs} runs"


if __name__ == "__main__":
    print(line())
    print(top_item_line())
    print(json.dumps(read_counter()))
