"""Add the Done-when clause to the G28 backlog line.

The line had a pre-registration and no clause. done_check reads the clause
as it was at the claim, so this is committed alone, before the claim and
before any number is computed.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "Not yet scored. Cross-sectional, on data/panel_xs_laevitas."
CLAUSE = (
    " Done when a committed script scores the pre-registered cell on "
    "data/panel_xs_laevitas for the cache's names, three periods, "
    "non-overlapping t-stat, net of the thin-tier round trip; the results "
    "file is written by that script through write_result and carries a "
    "verdict; a price change after day t leaves the signal at t unchanged."
)


def main():
    text = open(PATH).read()
    line = next(ln for ln in text.splitlines()
                if ln.startswith("2. xs_obv_xs_rank_below_10_ret_10. "))
    if "Done when" in line:
        raise SystemExit("clause already present")
    if ANCHOR not in line:
        raise SystemExit("anchor missing")
    updated = line.replace(ANCHOR, ANCHOR + CLAUSE, 1)
    open(PATH, "w").write(text.replace(line, updated, 1))
    print("clause added")


if __name__ == "__main__":
    main()
