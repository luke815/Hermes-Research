"""A6: write the shared counter from the sweep files and record the counts.

Reads every results/sweeps/*.csv dated on or after the last admission, counts
the distinct cell ids, writes results/sweeps/counter.json through the counter
module, mirrors the line into ops/sweep_status, and writes the results file.
The digest reads the same counter, so its line and the status line match.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regime_tester.counter import (  # noqa: E402
    LAST_ADMISSION, STATUS, read_counter, status_text, write_counter,
)
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    payload = write_counter()
    line = status_text(payload)
    tmp = STATUS + ".tmp"
    with open(tmp, "w") as handle:
        handle.write(line + "\n")
    os.replace(tmp, STATUS)
    digest_line = status_text(read_counter())
    result = {
        "scored": payload["scored"],
        "since": payload["since"],
        "last_admission": LAST_ADMISSION,
        "files_counted": len(payload["files"]),
        "files": payload["files"],
        "counter_file": payload["file"],
        "status_line": line,
        "digest_line": digest_line,
        "lines_match": line == digest_line,
        "queued_btc_event_cells_removed": [
            "btc_oi_share_chg7_top",
            "btc_alt_dispersion_z90_top",
            "btc_funding_persistence_top",
            "btc_volume_down_day_share_bottom",
        ],
    }
    path = write_result("a6_counter", result, inputs=["results/sweeps"])
    print(line)
    print(path)


if __name__ == "__main__":
    main()
