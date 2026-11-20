"""Put the A7 done-when clause on its item line, before the claim.

The clause is copied from the remaining parts of the item and from
research/HERMES_DATA_REVIEW_2026-11-17.md. It does not shorten anything.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "Done per test with its results file and verdict."
CLAUSE = (
    " Done when (1) results/<date>_a7_reversal.json scores 1-day and 3-day "
    "reversal on data/panel_xs_laevitas, one row per coin, names below $20M "
    "prior-bar open interest dropped, per-leg costs and carry, vol-scaled, "
    "three periods, with a verdict; (2) results/<date>_a7_derivatives.json "
    "scores skew, risk reversal, implied minus realized, basis, funding and "
    "OI change on BTC and ETH at 1 to 3 days and as a filter on (1), with a "
    "verdict; (3) results/<date>_a7_crowding.json scores pooled OI-to-volume "
    "above p90 and 30-day OI change before alt tops with date-clustered "
    "errors and a verdict; (4) results/<date>_a7_funding.json scores "
    "top-decile funding against forward returns with carry charged and a verdict."
)


def main():
    text = open(PATH).read()
    line = next(ln for ln in text.splitlines() if ln.startswith("- A7. "))
    if "Done when (1)" in line:
        raise SystemExit("clause already present")
    if ANCHOR not in line:
        raise SystemExit("anchor missing")
    updated = line.replace(ANCHOR, ANCHOR + CLAUSE, 1)
    open(PATH, "w").write(text.replace(line, updated, 1))
    print("clause written", len(CLAUSE))


if __name__ == "__main__":
    main()
