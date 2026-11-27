"""Count high and low across the whole panel the sweep reads.

scripts/x1_status.py checks the first 400 files in name order, and those are
not the Binance files the range backfill writes. This reads every file and
counts headers and values, then writes the count through write_result.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs_laevitas")


def main():
    files = [name for name in os.listdir(PANEL) if name.endswith(".csv")]
    with_header = 0
    with_value = 0
    for name in files:
        lines = open(os.path.join(PANEL, name)).read().splitlines()
        header = lines[0].split(",")
        if "high" not in header or "low" not in header:
            continue
        with_header += 1
        high_at = header.index("high")
        low_at = header.index("low")
        for line in lines[1:]:
            row = line.split(",")
            if ((high_at < len(row) and row[high_at])
                    or (low_at < len(row) and row[low_at])):
                with_value += 1
                break
    payload = {
        "item": "X1",
        "panel": "data/panel_xs_laevitas",
        "files": len(files),
        "with_high_low_header": with_header,
        "with_a_value": with_value,
    }
    path = write_result("x1_range_1300", payload, inputs=["data/panel_xs_laevitas"])
    print(path)


if __name__ == "__main__":
    main()
