"""Append the A7(1) pre-registration. No number is computed here."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "## Pass rules"
BLOCK = """## A7(1) pre-registration

Hypothesis: yesterday's losers among liquid coins outperform yesterday's winners over the next 1 and 3 days, after costs, and the edge is not an illiquid-name effect.

Panel: data/panel_xs_laevitas. One row per base coin, the venue whose file has the most days. A name is in on a date only if that file has a close that date. Names whose prior-bar open interest is below 20,000,000 dollars are dropped that date. A missing open interest drops the name; it is never filled.

Rule: the signal at date t is the negative of the close-to-close return over the window ending yesterday (closes through t-1). Windows 1 and 3 days. The book is long the top decile of that signal and short the bottom decile, equal weight, rebalanced daily. Each leg is scaled by the inverse of its own trailing 30-day realized volatility, known at t-1, so a name with no 30-day vol is left out.

Target: the forward return starting at today's close, horizons 1 and 3 days, minus BTC's return over the same window. Net of the costs table on both legs (fee and slippage by the prior-bar open-interest tier) and of each leg's funding carry over the holding window. A missing funding value leaves that leg's net missing; it is not treated as zero.

Periods: train to 2024-06-30, validation 2024-07-01 to 2025-12-31, test 2026-01-01 onward. t-stats use non-overlapping windows, every h-th day for an h-day horizon, and the independent count is reported beside the spread. A date with fewer than 20 names above the floor is skipped.

Pass: the decile spread keeps its sign in validation and in test, the non-overlapping t-stat is at least 2 in both, and the independent count is at least 40 in each. Below the count is insufficient. A sign flip is rejected. Neighbours, scored and reported but not used for the verdict: the same rule with a 10,000,000 dollar floor and a 50,000,000 dollar floor.

"""


def main():
    text = open(PATH).read()
    if "## A7(1) pre-registration" in text:
        raise SystemExit("already present")
    if ANCHOR not in text:
        raise SystemExit("anchor missing")
    open(PATH, "w").write(text.replace(ANCHOR, BLOCK + ANCHOR, 1))
    print("prereg appended")


if __name__ == "__main__":
    main()
