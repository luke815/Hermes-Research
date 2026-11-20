"""Mark A7 blocked on the bad close and say what unblocks it."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKLOG = ROOT / "research" / "backlog.md"
MARKER = "- A7. First research after A1 to A4"
NOTE = (
    "Blocked 2026-11-20: the score is not a verdict because "
    "binance_1000PEPEUSDT closed at 0.005731 on 2026-01-13 against 0.000006 "
    "the day before, and that one print is the 3-day test spread. Unblocks "
    "when that close is corrected in data/panel_xs_laevitas and "
    "scripts/score_a7_reversal.py is rerun. A research run does not rewrite "
    "the panel. "
)


def main():
    text = BACKLOG.read_text()
    if NOTE in text:
        raise SystemExit("already marked")
    if MARKER not in text:
        raise SystemExit("marker not found")
    BACKLOG.write_text(text.replace(MARKER, NOTE + MARKER, 1))
    print("marked")


if __name__ == "__main__":
    main()
