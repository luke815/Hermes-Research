"""Put the D2 done-when clause on the item line, where done_check reads it."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKLOG = ROOT / "research" / "backlog.md"
OLD = "- D2. Funding units in one place."
CLAUSE = (
    "- D2. Funding units in one place. Done when the assertion exists and a "
    "test covers it."
)


def main():
    text = BACKLOG.read_text()
    if CLAUSE in text:
        raise SystemExit("already on one line")
    if OLD not in text:
        raise SystemExit("marker not found")
    BACKLOG.write_text(text.replace(OLD, CLAUSE, 1))
    print("rewritten")


if __name__ == "__main__":
    main()
