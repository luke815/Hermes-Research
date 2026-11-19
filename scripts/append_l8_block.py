"""Append the L8 block note, citing the results file the sum script wrote."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "Not done: ETH has no summed day yet, and the walk has not reached the last closed day."
NOTE = (" Blocked 2026-11-19: the walk is a pull and a research run does not pull. The liq_daily_sum daemon owns it. results/2026-11-19_l8_sum.json: BTC 171 days summed, first 2025-09-26, last 2026-03-15; ETH 0 days; remaining 1. Unblocks when that file shows ETH days summed and remaining 0.")


def main():
    text = open(BACKLOG).read()
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    open(BACKLOG, "w").write(text.replace(ANCHOR, ANCHOR + NOTE, 1))
    print("backlog updated", os.path.getsize(BACKLOG))


if __name__ == "__main__":
    main()
