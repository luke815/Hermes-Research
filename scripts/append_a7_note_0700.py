"""Append the A7(1) reading to the backlog item line.

The score ran and the result is not a verdict: one bad close carries the
3-day test spread. The line records that and what unblocks it.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKLOG = ROOT / "research" / "backlog.md"
MARKER = "The pre-registration is commit 2d78832. "
NOTE = (
    "Read 2026-11-20 07:43 UTC: scripts/score_a7_reversal.py wrote "
    "results/2026-11-20_a7_reversal.json, 3,781 coins, lookahead passed at "
    "2024-01-20. Not a verdict. The 3-day window at the 3-day horizon reports "
    "an 83.21 percent test spread, and results/2026-11-20_a7_reversal_outlier.json "
    "traces it to one name: binance_1000PEPEUSDT closed at 0.005731 on "
    "2026-01-13 against 0.000006 the day before and 0.000007 the day after. "
    "The longest file wins, so that print is the PEPE column. Unblocks when "
    "that close is corrected and the score is rerun. "
)


def main():
    text = BACKLOG.read_text()
    if MARKER not in text:
        raise SystemExit("marker not found")
    BACKLOG.write_text(text.replace(MARKER, NOTE + MARKER, 1))
    print("appended")


if __name__ == "__main__":
    main()
