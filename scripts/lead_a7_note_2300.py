"""Move the 23:00 A7 note to the front of the item line.

The header restore left the note at the end of the line, after the done-when
clause, with no space before it. A reader takes the first sentence as the
current state, so the latest reading has to lead.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
NOTE = "Rechecked 2026-11-21 23:00 UTC:"


def main():
    text = open(BACKLOG).read()
    line = next(ln for ln in text.splitlines() if ln.startswith("- A7. "))
    at = line.find(NOTE)
    if at < 0:
        raise SystemExit("23:00 note missing")
    if line.startswith("- A7. " + NOTE):
        raise SystemExit("note already leads")
    body = line[len("- A7. "):at]
    note = line[at:]
    if not note.endswith(" "):
        note += " "
    restored = "- A7. " + note + body
    open(BACKLOG, "w").write(text.replace(line, restored, 1))
    print(restored[:160])


if __name__ == "__main__":
    main()
