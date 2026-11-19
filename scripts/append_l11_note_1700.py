"""Append this run's reading of L11 to its backlog line."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = ("Not done: the clause asks for history from 2021 and the vendor's "
          "files start 2021-08-07.")
NOTE = (" Rechecked 2026-11-19 17:00 UTC: results/2026-11-19_l11_coverage.json "
        "counts 499 dead names, 484 panel files, 15 missing, and 81 names with "
        "funding, open interest and basis from 2021, earliest 2021-08-07. The "
        "other 403 covered names start later because they listed later. The "
        "vendor serves nothing earlier, so the from-2021 part cannot be met by "
        "a pull. Blocked on the vendor's start date.")


def main():
    text = open(PATH).read()
    if NOTE.strip() in text:
        raise SystemExit("note already present")
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    open(PATH, "w").write(text.replace(ANCHOR, ANCHOR + NOTE, 1))
    print("appended")


if __name__ == "__main__":
    main()
