"""Write B1's done-when clause before the claim reads it.

The clause is the spec's remaining parts: sector tags, the beta table, the
universe extended to 150, and the liquidity and exclusion filters. Each part
names the file that proves it.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
MARKER = "- B1. Sector tags from CoinGecko, the beta table, the universe extended to the top 150 by open interest, and the liquidity and exclusion filters. One run."
CLAUSE = (
    " Done when data/sectors.json carries a sector for every name in the "
    "universe; data/betas.json carries a beta and an r2 for every name with "
    "60 daily bars; data/universe_top150.json holds 150 names, one venue per "
    "coin, ranked by open interest; data/book_universe.json marks each name "
    "long_ok or short_ok against the open-interest and volume floors and "
    "excludes stables, wrapped assets and names listed under 30 days; and "
    "results/<date>_b1.json is written by the script that computed them."
)


def main():
    text = open(PATH).read()
    if "Done when data/sectors.json carries a sector" in text:
        raise SystemExit("clause already present")
    if MARKER not in text:
        raise SystemExit("marker not found")
    open(PATH, "w").write(text.replace(MARKER, MARKER + CLAUSE, 1))
    print("clause written")


if __name__ == "__main__":
    main()
