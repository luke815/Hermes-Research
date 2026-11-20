"""Append the funding units line to data/COVERAGE.md."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "data" / "COVERAGE.md"
LINE = (
    "\nFunding units. Dashboard funding columns are percent per 8h, where 0.01 is "
    "1 bp. The Laevitas perp_funding pull is the same scale on daily bars and "
    "one hundredth of it on hourly bars: the saved daily median is 0.00704 and "
    "the saved hourly median is 0.0000386. scripts/fetch_laevitas.py refuses a "
    "daily pull whose median is outside 0.001 to 0.05.\n"
)


def main():
    text = PATH.read_text()
    if "Funding units." in text:
        raise SystemExit("already written")
    PATH.write_text(text.rstrip() + "\n" + LINE)
    print("written")


if __name__ == "__main__":
    main()
