"""Correct the 15:00 B3 note so it matches the results file.

results/2026-11-22_b3_inputs_1500.json shows the hourly store last bar
2026-11-22, 0 days behind. The note appended by record_b3_inputs_1500.py
said all four inputs were past the limit. This replaces that sentence with
what the file shows. It does not recompute and it does not pull.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
WRONG = ("and the hourly store last bar 2026-11-22 (0 days behind). All "
         "four are past the two-day freshness limit, and no registered "
         "daemon refreshes them.")
RIGHT = ("and the hourly store last bar 2026-11-22 (0 days behind). The "
         "daily bars, the universe and the betas are past the two-day "
         "freshness limit; the hourly store is not. No registered daemon "
         "refreshes the book inputs.")


def main():
    text = open(BACKLOG).read()
    line = next(ln for ln in text.splitlines() if ln.startswith("- B3. "))
    if WRONG not in line:
        raise SystemExit("the sentence to correct is not in the B3 line")
    updated = line.replace(WRONG, RIGHT, 1)
    open(BACKLOG, "w").write(text.replace(line, updated, 1))
    print("corrected")


if __name__ == "__main__":
    main()
