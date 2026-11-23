"""Give the force-index queue line a G32 header and a Done-when clause.

The line is numbered, so no run can claim it. The clause is copied from the
pre-registration in research/generated.md item 32. This script writes no number.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
OLD = (
    "6. xs_force_13_z_30_below_20_rel_1. Pre-registered 2026-11-22 "
    "in research/generated.md, item 32. Not yet scored. Cross-sectional, "
    "on data/panel_xs_laevitas."
)
NEW = (
    "- G32. xs_force_13_z_30_below_20_rel_1. Pre-registered 2026-11-22 "
    "in research/generated.md, item 32. Not yet scored. Cross-sectional, "
    "on data/panel_xs_laevitas. Done when a committed script scores the "
    "pre-registered cell on data/panel_xs_laevitas for the cache's names, "
    "three periods, non-overlapping t-stat, net of the thin-tier round trip; "
    "the results file is written by that script through write_result and "
    "carries a verdict; a price change after day t leaves the signal at t "
    "unchanged."
)


def main():
    text = open(PATH).read()
    if text.count(OLD) != 1:
        raise SystemExit(f"anchor count {text.count(OLD)}")
    if "- G32. " in text:
        raise SystemExit("G32 header already present")
    open(PATH, "w").write(text.replace(OLD, NEW, 1))
    print("rewritten")


if __name__ == "__main__":
    main()
