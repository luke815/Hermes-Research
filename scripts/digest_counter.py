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


def line():
    return status_text(read_counter())


if __name__ == "__main__":
    print(line())
    print(json.dumps(read_counter()))
