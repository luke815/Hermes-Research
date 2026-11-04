"""Sort every saved OKX price file by date, keeping the header first.

The pull appends days as they finish, and they finish out of order, so the
saved files are not date-ordered. This rewrites each file in date order.
"""

import csv
from pathlib import Path

OUT = Path("/opt/data/workspace/regime-tester/data/okx_prices")


def main() -> None:
    rewritten = 0
    rows = 0
    for path in sorted(OUT.glob("*.csv")):
        with open(path, newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader)
            body = sorted(reader, key=lambda row: row[0])
        dates = [row[0] for row in body]
        if len(dates) != len(set(dates)):
            raise SystemExit(f"{path.name}: duplicate dates")
        with open(path, "w", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(header)
            writer.writerows(body)
        rewritten += 1
        rows += len(body)
    print(f"sorted {rewritten} files, {rows} rows")


if __name__ == "__main__":
    main()
