"""Record this run's reading of D3 on its backlog line.

The clause names hourly.pkl. This script checks whether that file, or the
hourly CSVs it is built from, exist, and records the finding. It does not pull.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
HOURLY = os.path.join(ROOT, "research", "outside", "data", "hourly.pkl")
LAE = os.path.join(ROOT, "research", "outside", "data", "laevitas")
ANCHOR = "or the harness masks it and says so."


def main():
    present = os.path.exists(HOURLY)
    hourly_csvs = 0
    if os.path.isdir(LAE):
        hourly_csvs = len([n for n in os.listdir(LAE) if n.endswith("_1h.csv")])
    if present:
        raise SystemExit("hourly.pkl exists; this note is the blocked reading")
    text = open(PATH).read()
    marker = "Rechecked 2026-11-20 09:00 UTC: research/outside/data/hourly.pkl"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ANCHOR in ln)
    note = (
        " Rechecked 2026-11-20 09:00 UTC: research/outside/data/hourly.pkl is "
        f"absent and research/outside/data/laevitas holds {hourly_csvs} hourly "
        "CSVs, so there is nothing to mask and nothing to backfill from. The "
        "Laevitas hourly store is a pull, and a research run does not pull. "
        "Blocked on the hourly files. Unblocks when hourly.pkl exists or the "
        "harness masks the window and says so."
    )
    open(PATH, "w").write(text.replace(line, line + note, 1))
    print("appended")


if __name__ == "__main__":
    main()
