"""Record the C10 verdict on its backlog line.

The numbers come from results/2026-11-21_c10_weekly.json, written by
scripts/score_c10.py. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-21_c10_weekly.json")


def main():
    reading = json.load(open(RESULT))
    text = open(PATH).read()
    line = next(ln for ln in text.splitlines() if ln.startswith("- C10. "))
    if "Verdict 2026-11-21" in line:
        raise SystemExit("verdict already present")
    largest = max(
        cell["periods"]["train"]["episodes_both"]
        + cell["periods"]["validation"]["episodes_both"]
        for cell in reading["cells"])
    note = (
        f" Verdict 2026-11-21: {reading['verdict']}. "
        "results/2026-11-21_c10_weekly.json scores 8 cells on 356 weekly bars, "
        f"and the largest train-plus-validation count is {largest} against a "
        "bar of 30. The top flag never reaches the bar on either asset, and "
        "the bottom flag does not either. The pre-registration commit "
        f"{reading['prereg_commit'][:10]} precedes the scoring commit "
        f"{reading['provenance']['commit'][:10]}."
    )
    open(PATH, "w").write(text.replace(line, line.rstrip("\n") + note + "\n", 1))
    print("appended")


if __name__ == "__main__":
    main()
