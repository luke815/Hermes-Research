"""Paste the done_check line onto the D2 item."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKLOG = ROOT / "research" / "backlog.md"
OLD = "Done when the assertion exists and a test covers it."
NEW = (
    "Done when the assertion exists and a test covers it. "
    "Done 2026-11-20. done_check 8c4149bf21."
)


def main():
    text = BACKLOG.read_text()
    if "done_check 8c4149bf21." in text:
        raise SystemExit("already pasted")
    if OLD not in text:
        raise SystemExit("marker not found")
    BACKLOG.write_text(text.replace(OLD, NEW, 1))
    print("pasted")


if __name__ == "__main__":
    main()
