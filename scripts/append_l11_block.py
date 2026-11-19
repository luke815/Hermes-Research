"""Append the L11 block note, citing the results file written this run."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "It needs its own puller, which a later run builds and a daemon runs."
NOTE = (" Built 2026-11-19: scripts/delisted_pull.py, daemon delisted_pull. Blocked on the pull: results/2026-11-19_l11_pull.json counts 499 dead names (31 Binance, 314 Bybit, 154 OKX) and 8 files saved, 491 remaining. Unblocks when that remaining count is 0 and the saved history is merged into panel_xs_laevitas, which the daemon does, not a research run.")


def main():
    text = open(BACKLOG).read()
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    open(BACKLOG, "w").write(text.replace(ANCHOR, ANCHOR + NOTE, 1))
    print("backlog updated", os.path.getsize(BACKLOG))


if __name__ == "__main__":
    main()
