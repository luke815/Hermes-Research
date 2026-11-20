"""Record this run's reading of A7 on its backlog line.

A7(1) stays blocked on the bad close, which a research run does not rewrite.
A7(3) stays blocked because the alt derivs_summary files are not on disk.
This script only records the reading.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
PANEL = os.path.join(ROOT, "data", "panel_xs_laevitas", "binance_1000PEPEUSDT.csv")
MARKET = os.path.join(ROOT, "data", "laevitas", "market")
ANCHOR = ("A7(3) is blocked: data/laevitas/market has no derivs_summary for "
          "ADA, SOL, LINK, XRP or AVAX. A7(1) stays blocked on the bad close. ")
NAMES = ("ADA", "SOL", "LINK", "XRP", "AVAX")


def main():
    import csv
    with open(PANEL) as handle:
        rows = list(csv.DictReader(handle))
    by_date = {row["date"]: row for row in rows}
    bad = by_date["2026-01-13"]["close"]
    before = by_date["2026-01-12"]["close"]
    after = by_date["2026-01-14"]["close"]
    if bad == before:
        raise SystemExit("the bad close is gone; this note is the blocked reading")
    missing = [name for name in NAMES
               if not any(fn.startswith(f"derivs_summary_{name}_")
                          for fn in os.listdir(MARKET))]
    if not missing:
        raise SystemExit("the alt summaries are on disk; this note is the blocked reading")
    text = open(PATH).read()
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    note = (
        "Rechecked 2026-11-20 13:00 UTC: binance_1000PEPEUSDT still closes at "
        f"{bad} on 2026-01-13 against {before} the day before and {after} the "
        f"day after, so A7(1) stays blocked. A7(3) stays blocked: "
        f"data/laevitas/market has no derivs_summary for {', '.join(missing)}. "
        "A research run does not pull and does not rewrite the panel. "
    )
    open(PATH, "w").write(text.replace(ANCHOR, ANCHOR + note, 1))
    print("appended", bad, before, after, missing)


if __name__ == "__main__":
    main()
