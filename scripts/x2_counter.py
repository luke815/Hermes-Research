"""X2: the digest line and the sweep status line, read from the files.

Both are built by status_text from results/sweeps/counter.json. This reads
the status file and recomputes the digest line, and writes the comparison.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.counter import read_counter, status_text  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUS = os.path.join(ROOT, "ops", "sweep_status")


def main():
    status_line = open(STATUS).read().strip()
    digest_line = status_text(read_counter())
    out = {
        "item": "X2",
        "status_line": status_line,
        "digest_line": digest_line,
        "same_line": status_line == digest_line,
        "counter_file": read_counter().get("file"),
        "scored": read_counter().get("scored"),
        "testable": read_counter().get("testable"),
    }
    path = write_result("x2_counter", out, inputs=[
        "ops/sweep_status", "results/sweeps/counter.json"])
    print(path)


if __name__ == "__main__":
    main()
