"""Record this run's reading of the A7(1) close, from the panel file itself.

A research run does not rewrite the panel and does not rescore. This reads
the three closes and writes them through write_result, then appends the
block note to the A7 line.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs_laevitas", "binance_1000PEPEUSDT.csv")
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
DATES = ("2026-01-12", "2026-01-13", "2026-01-14")


def closes():
    lines = open(PANEL).read().splitlines()
    header = lines[0].split(",")
    close_at = header.index("close")
    found = {}
    for line in lines[1:]:
        row = line.split(",")
        if row[0] in DATES:
            found[row[0]] = float(row[close_at])
    return found


def main():
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    found = closes()
    bad = found.get("2026-01-13")
    still_bad = (
        bad is not None and bad > 0.001
        and found.get("2026-01-12", 1) < 0.0001
        and found.get("2026-01-14", 1) < 0.0001)
    payload = {
        "item": "A7",
        "today": today,
        "read_at": stamp,
        "file": "data/panel_xs_laevitas/binance_1000PEPEUSDT.csv",
        "mtime": datetime.fromtimestamp(
            os.stat(PANEL).st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "closes": found,
        "still_bad": still_bad,
    }
    path = write_result("a7_close", payload, inputs=[
        "data/panel_xs_laevitas/binance_1000PEPEUSDT.csv"])
    print(path)
    if not still_bad:
        raise SystemExit("close is no longer the bad print; not marking blocked")
    text = open(BACKLOG).read()
    marker = "Rechecked 2026-11-21 07:00 UTC: results/2026-11-21_a7_close.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- A7. "))
    anchor = "scripts/score_a7_reversal.py is rerun."
    if anchor not in line:
        raise SystemExit("anchor missing from the A7 line")
    note = (
        " Rechecked 2026-11-21 07:00 UTC: results/2026-11-21_a7_close.json "
        f"shows the close on 2026-01-13 is {found['2026-01-13']} against "
        f"{found['2026-01-12']} on 2026-01-12 and {found['2026-01-14']} on "
        f"2026-01-14, file mtime {payload['mtime']}. A7(1) stays blocked. "
        "Unblocks when that close is corrected in data/panel_xs_laevitas and "
        "scripts/score_a7_reversal.py is rerun. A research run does not "
        "rewrite the panel."
    )
    updated = line.replace(anchor, anchor + note, 1)
    open(BACKLOG, "w").write(text.replace(line, updated, 1))
    print("noted")


if __name__ == "__main__":
    main()
