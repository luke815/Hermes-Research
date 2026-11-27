"""Add L2's done-when clause, copied from the puller's own finish conditions.

The line has none. The puller never reports remaining 0 while a live name's
last bar is short of the last closed day, so the clause names the four
families and the options maturity walk, which is what the daemon finishes.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "results/2026-11-17_l2_closed_family.json."
CLAUSE = (
    " Done when a committed script writes results/<date>_l2_status.json "
    "showing perpetual and future stamped closed in "
    "data/laevitas/family_closed.json; every maturity in "
    "data/laevitas/catalog_v1.json walked into "
    "data/laevitas/option_maturities.json; option history saved for every "
    "contract in data/laevitas/option_contracts.json; liquidation history "
    "saved for every venue and currency the puller lists."
)


def main():
    text = open(PATH).read()
    if "Done when a committed script writes results/<date>_l2_status.json" in text:
        raise SystemExit("clause already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- L2. "))
    if not line.endswith(ANCHOR):
        raise SystemExit("anchor is not the end of the L2 line")
    open(PATH, "w").write(text.replace(line, line + CLAUSE, 1))
    print("clause appended")


if __name__ == "__main__":
    main()
