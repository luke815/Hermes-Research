"""Record why Q2 did not close this run.

done_check refused the close. This script only records that reading.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "against a bar of 20."


def main():
    text = open(PATH).read()
    marker = "Rechecked 2026-11-21 04:00 UTC: done_check refused Q2"
    if marker in text:
        raise SystemExit("note already present")
    lines = text.splitlines(keepends=True)
    index = next(i for i, ln in enumerate(lines) if ANCHOR in ln and "Q2" in "".join(lines[max(0, i - 4):i + 1]))
    note = (
        " Rechecked 2026-11-21 04:00 UTC: done_check refused Q2. The clause "
        "sits on the line after the item header, so it reads as no Done-when "
        "clause, and no script changed since the claim at 57c3f71. The results "
        "file itself meets both parts: results/2026-11-20_q2_skew_no_vol.json "
        "carries 10 cells with the two fresh windows separate, and its "
        "prereg_commit 35cec2d673 is an ancestor of its scoring commit "
        "28bb40f5e6. The claim was released. Not done."
    )
    lines[index] = lines[index].rstrip("\n") + note + "\n"
    open(PATH, "w").write("".join(lines))
    print("appended")


if __name__ == "__main__":
    main()
