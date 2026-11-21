"""Put the A7 item header back on its own line.

A note script appended "- A7. ..." onto the continuation line that follows
the A5 item. The stall check and the claim reader only see a line that
starts with "- A7.", so the item was invisible. This splits that line and
does not change any word of either item.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
MARKER = "panel. - A7. First research after A1 to A4"


def main():
    text = open(PATH).read()
    if text.count(MARKER) != 1:
        raise SystemExit(f"marker count {text.count(MARKER)}")
    if "\n- A7. First research after A1 to A4" in text:
        raise SystemExit("already split")
    open(PATH, "w").write(text.replace(MARKER, "panel.\n- A7. First research after A1 to A4", 1))
    print("split")


if __name__ == "__main__":
    main()
