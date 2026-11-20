"""Append this run's reading of X1 to its backlog line."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "sweep_xs pid 3166, version fd0b898, is rebuilding its cache."
NOTE = (" Rechecked 2026-11-19 17:00 UTC: the duplicate was the same cell id "
        "scored on an older universe, which scored_ids drops and append_rows "
        "then read as a second writer. scripts/sweep_xs.py now keeps the new "
        "universe's row and skips that check for an id an older file holds. "
        "tests/test_sweep_worklist.py, 8 passed. Restarted as pid 9307, version "
        "f1f30f0, stale_code false, and its first cycle is rebuilding the cache "
        "with no error. results/2026-11-19_x1_status.json shows cells per hour "
        "not above 5,000. Not done: the status line has not shown that rate for "
        "one full hour.")


def main():
    text = open(PATH).read()
    if "pid 9307" in text:
        raise SystemExit("note already present")
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    open(PATH, "w").write(text.replace(ANCHOR, ANCHOR + NOTE, 1))
    print("appended")


if __name__ == "__main__":
    main()
