"""Add the missing Done-when clauses to B3, B4 and B5.

The clauses are copied from research/LONG_SHORT_BOOK.md sections 5, 6, 7
and 9, which is where those items are specified. Each part names the file
or the number that proves it. This script only writes the clauses; it does
not score and it does not pull. Committed before any claim of those items,
because done_check reads the clause as it stood at the claim.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")

CLAUSES = {
    "- B3. ": (
        "Done when a committed script pairs each long leg against a short "
        "leg in the same sector, else against that sector's most liquid "
        "name or BTC; the hedge ratio is the 60-day beta to BTC, capped at "
        "1.5 and floored at 0.5, and a pair whose beta has r-squared below "
        "0.3 uses inverse 30-day volatility and says so; size per name is "
        "the risk budget divided by 30-day volatility with shorts at 0.8 "
        "times the long size; the book key's pairs array carries the hedge "
        "ratio and the carry, and the stats carry net beta within 0.1, no "
        "sector above 30 percent of gross and no name above 10 percent; "
        "results/<date>_b3_book.json is written by that script through "
        "write_result and names each pair with its hedge ratio, its sizing "
        "method and its carry."),
    "- B4. ": (
        "Done when a committed script runs the book rule through "
        "regime_tester/strategy.py on the point-in-time universe, weekly "
        "rebalance, net of the costs table and funding carry, for the six "
        "variants (full rule, long leg only, short leg only, without the "
        "funding filters, without the beta hedge, equal weight); "
        "results/<date>_b4_backtest.json is written by that script through "
        "write_result and carries the three periods and the per-year table "
        "for each variant, with the admission verdict against a positive "
        "net Sharpe in validation and test, a drawdown below the naive "
        "decile's in both, and the filtered rule beating the naive rule in "
        "validation."),
    "- B5. ": (
        "Done when a committed script records the 4-hour entry beside the "
        "simple entry for every open leg: a long entered on a 4-hour close "
        "above its 4-hour 20-bar high with volume confirmation, else at the "
        "open of the window if that does not come within two days, and a "
        "short on the mirror; signals/book.csv carries the entry rule used "
        "on each row; results/<date>_b5_timing.json is written by that "
        "script through write_result and names each leg with both entry "
        "prices."),
}


def main():
    text = open(BACKLOG).read()
    lines = text.splitlines()
    changed = []
    for prefix, clause in CLAUSES.items():
        matches = [i for i, line in enumerate(lines) if line.startswith(prefix)]
        if len(matches) != 1:
            raise SystemExit(f"{prefix} matched {len(matches)} lines")
        at = matches[0]
        if "Done when" in lines[at]:
            raise SystemExit(f"{prefix} already has a Done-when clause")
        head, _, rest = lines[at].partition(". ")
        title, _, tail = rest.partition(". ")
        if not title:
            raise SystemExit(f"{prefix} has no title sentence")
        lines[at] = f"{head}. {title}. {clause} {tail}"
        changed.append(prefix.strip("-. "))
    open(BACKLOG, "w").write("\n".join(lines) + "\n")
    print("clauses added:", ", ".join(changed))


if __name__ == "__main__":
    main()
