"""Append this run's reading of X1 to its backlog line."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "Not done: the status line has not shown that rate for one full hour."
NOTE = (" Rechecked 2026-11-19 23:00 UTC: results/2026-11-19_x1_status.json "
        "shows the status line at cells per hour 0, 19,872 emittable cells "
        "still open on the 234-name universe, 4,752 of them market-level "
        "series the cross-section must not score and 15,120 that need high "
        "and low. data/panel_xs_laevitas has neither column. The high_low "
        "daemon reports remaining 0 because it writes data/panel_xs, where "
        "919 of 923 Binance files carry both columns, and the sweep does not "
        "read that directory. Blocked on the range columns reaching the panel "
        "the sweep reads. Unblocks when that file shows cells per hour above "
        "5,000.")


def main():
    text = open(PATH).read()
    if "19,872 emittable" in text:
        raise SystemExit("note already present")
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    open(PATH, "w").write(text.replace(ANCHOR, ANCHOR + NOTE, 1))
    print("appended")


if __name__ == "__main__":
    main()
