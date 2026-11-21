"""Join D3's clause onto its item line and record this run's reading.

The stall check only reads the line that starts with "- D3.", and the
done-when clause plus every earlier reading sit on the lines after it, so
the item looks open and unread. This joins those lines, then appends this
run's reading of the hourly files. It does not pull.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
HOURLY = os.path.join(ROOT, "research", "outside", "data", "hourly.pkl")
LAE = os.path.join(ROOT, "research", "outside", "data", "laevitas")
MARKER = "Rechecked 2026-11-21 07:00 UTC: research/outside/data/hourly.pkl"


def main():
    present = os.path.exists(HOURLY)
    hourly_csvs = 0
    if os.path.isdir(LAE):
        hourly_csvs = len([n for n in os.listdir(LAE) if n.endswith("_1h.csv")])
    if present:
        raise SystemExit("hourly.pkl exists; this note is the blocked reading")
    lines = open(PATH).read().splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("- D3. "))
    end = start + 1
    while end < len(lines) and not lines[end].startswith("- ") and not lines[end].startswith("#"):
        end += 1
    joined = " ".join(ln.strip() for ln in lines[start:end])
    if MARKER in joined:
        raise SystemExit("note already present")
    note = (
        " Rechecked 2026-11-21 07:00 UTC: research/outside/data/hourly.pkl is "
        f"absent and research/outside/data/laevitas holds {hourly_csvs} hourly "
        "CSVs, so there is nothing to mask and nothing to backfill from. No "
        "registered daemon pulls the Laevitas hourly store, and a research run "
        "does not pull. Blocked on the hourly files. Unblocks when hourly.pkl "
        "exists or the harness masks the window and says so."
    )
    lines[start:end] = [joined + note]
    open(PATH, "w").write("\n".join(lines) + "\n")
    print(f"joined {end - start} lines, hourly_csvs={hourly_csvs}")


if __name__ == "__main__":
    main()
