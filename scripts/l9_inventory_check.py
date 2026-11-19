"""Check the L9 inventory against the files it claims to describe.

data/INVENTORY.md is written by scripts/market_backfill.py from
data/laevitas/market. This recomputes the coverage from those files and
compares it to the inventory line by line, so the results file says whether
the inventory matches the store rather than repeating the file by hand.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import market_backfill  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INVENTORY = os.path.join(ROOT, "data", "INVENTORY.md")


def inventory_lines():
    """The series lines, keyed by the series name the file names."""
    out = {}
    for line in open(INVENTORY):
        if not line.startswith("- "):
            continue
        name, _, rest = line[2:].partition(":")
        out[name.strip()] = rest.strip()
    return out


def main():
    rows = market_backfill.coverage()
    lines = inventory_lines()
    mismatches = []
    for row in rows:
        if row["first"] is None:
            expected = f"no file yet, expected from {row['expected_first']}"
        else:
            expected = (f"first {row['first']}, last {row['last']}, "
                        f"{row['rows']} rows, {row['missing_days']} missing days")
        if lines.get(row["series"]) != expected:
            mismatches.append({"series": row["series"], "inventory": lines.get(row["series"]),
                               "store": expected})
    out = {
        "item": "L9",
        "inventory": "data/INVENTORY.md",
        "series": len(rows),
        "series_in_inventory": len(lines),
        "mismatches": len(mismatches),
        "mismatch_rows": mismatches,
        "coverage": rows,
        "matches": not mismatches and len(lines) == len(rows),
    }
    path = write_result("l9_inventory", out, inputs=["data/laevitas/market", "data/INVENTORY.md"])
    print(json.dumps({k: v for k, v in out.items() if k not in ("coverage", "mismatch_rows")}))
    print(path)


if __name__ == "__main__":
    main()
