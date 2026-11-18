"""The daily digest's counter line, read from the sweep's counter file.

Prints the scored and testable counts and the file they came from, so the
digest cites the same file and number as ops/sweep_status.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.counter import read_counter  # noqa: E402


def line():
    counter = read_counter()
    return (f"cells scored {counter['scored']} of {counter['testable']} testable, "
            f"from {counter['file']}")


if __name__ == "__main__":
    print(line())
    print(json.dumps(read_counter()))
