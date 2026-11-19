"""Append this run's reading of A5 to its backlog line."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "Unblocks when that file shows the flag false across a full day."
NOTE = (" Rechecked 2026-11-19 13:00 UTC: results/2026-11-19_a5_span.json shows "
        "rs_stale false at 2026-11-19T13:04:19Z with a false span of 0.0 hours "
        "over 1 reading. The flag is not recorded anywhere before today, so the "
        "full day cannot be shown yet. Unblocks when that file shows full_day true.")
ANCHOR = ("Unblocks when that file shows the flag false across a full day.\n- A7.")


def main():
    text = open(PATH).read()
    if NOTE.strip() in text:
        raise SystemExit("note already present")
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    open(PATH, "w").write(text.replace(ANCHOR, ANCHOR.replace("\n- A7.", NOTE + "\n- A7."), 1))
    print("appended")


if __name__ == "__main__":
    main()
