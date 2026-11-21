"""Put the A7 header back at the start of its line.

scripts/record_a7_block_2300.py found the line by the header and prepended
the note, which moved the header off the start of the line. The stall check
reads the first line that starts with an item header, so a buried header is
invisible and the next item is reported as the top. This restores the header
and leaves the note after it.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
HEADER = "- A7. "


def main():
    text = open(BACKLOG).read()
    if any(line.startswith(HEADER) for line in text.splitlines()):
        raise SystemExit("header already at the start of a line")
    line = next(ln for ln in text.splitlines() if HEADER in ln)
    at = line.index(HEADER)
    restored = HEADER + line[at + len(HEADER):] + line[:at]
    open(BACKLOG, "w").write(text.replace(line, restored, 1))
    print("restored", restored[:80])


if __name__ == "__main__":
    main()
