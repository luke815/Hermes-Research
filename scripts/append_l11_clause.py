"""Add the L11 Done-when clause, copied from the spec, before any work on it.

The clause is the one research/HERMES_DATA_REVIEW_2026-11-17.md states, split
into parts so each can be evidenced. It is committed on its own, before the
claim, because done_check reads the clause as it stood at the claim.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "- L11. Delisted names. "
CLAUSE = ("Done when a committed puller fetches Laevitas per-symbol history for the delisted names in the Binance, Bybit and OKX span files; "
          "the fetched history is merged into panel_xs_laevitas; "
          "A4's universe has funding, open interest and basis for the dead names from 2021.")


def main():
    text = open(BACKLOG).read()
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    line_end = text.index("\n", text.index(ANCHOR))
    line = text[text.index(ANCHOR):line_end]
    if "Done when" in line:
        raise SystemExit("clause already present")
    text = text[:line_end] + " " + CLAUSE + text[line_end:]
    open(BACKLOG, "w").write(text)
    print("clause added", os.path.getsize(BACKLOG))


if __name__ == "__main__":
    main()
