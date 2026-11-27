"""Put P3's done-when clause on its backlog line, before the claim reads it.

The clause was missing. This script only adds it.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
OLD = ("- P3. The pair-rule backtest through strategy.py, three periods, per "
       "year, net of costs and carry. After L6. Done when the result file "
       "shows the admission verdict and bt_sharpe is written for an admitted "
       "pair type.")
NEW = (OLD + " Done when a committed script scores the pre-registered "
       "reversion rule and the relative-strength rule on the point-in-time "
       "panel, three periods, per year, net of costs on both legs and funding "
       "carry; the results file is written by that script through write_result "
       "and carries an admission verdict; bt_sharpe is written into pairs_board "
       "for a pair type that is admitted and left null otherwise.")


def main():
    text = open(PATH).read()
    if OLD not in text:
        raise SystemExit("P3 line not found")
    if text.count(OLD) != 1:
        raise SystemExit("P3 line is not unique")
    open(PATH, "w").write(text.replace(OLD, NEW, 1))
    print("clause added")


if __name__ == "__main__":
    main()
