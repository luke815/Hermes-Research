"""Add the missing Done-when parts to P1 before it is worked.

done_check reads the clause as it was at the claim, and a clause with no
semicolon is one part. The spec names three things the key must carry, so the
clause names them, and this commit lands before the script that builds the key.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
OLD = ("- P1. pair_inputs for every name clearing the liquidity floor, from the "
       "Laevitas panel. Done when the calculator's name list on the page shows "
       "the universe count.")
NEW = ("- P1. pair_inputs for every name clearing the liquidity floor, from the "
       "Laevitas panel. Done when the calculator's name list on the page shows "
       "the universe count; the key covers every coin clearing the floor plus "
       "BTC and ETH, one venue each; closes are the last 250 days from the "
       "venue with the most days above the floor.")


def main():
    text = open(PATH).read()
    if text.count(OLD) != 1:
        raise SystemExit(f"anchor count {text.count(OLD)}")
    open(PATH, "w").write(text.replace(OLD, NEW, 1))
    print("clause written")


if __name__ == "__main__":
    main()
