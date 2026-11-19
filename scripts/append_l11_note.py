"""Append this run's reading of L11 to its backlog line."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "What remains is the merge into panel_xs_laevitas, which no script does yet."
NOTE = (" Merged 2026-11-19: scripts/merge_delisted.py wrote the saved history "
        "into a new directory and data_guard swapped it in, 482 files added, "
        "none removed or shrunk, previous kept as "
        "data/panel_xs_laevitas.prev-20261119T130750Z. "
        "results/2026-11-19_l11_merge.json: 484 of 499 dead names covered, "
        "15 with no history from the vendor, 0 missing files, earliest first "
        "bar 2021-08-07, 81 names with a bar before 2022. Not done: the clause "
        "asks for history from 2021 and the vendor's files start 2021-08-07.")


def main():
    text = open(PATH).read()
    if "results/2026-11-19_l11_merge.json" in text:
        raise SystemExit("note already present")
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    open(PATH, "w").write(text.replace(ANCHOR, ANCHOR + NOTE, 1))
    print("appended")


if __name__ == "__main__":
    main()
