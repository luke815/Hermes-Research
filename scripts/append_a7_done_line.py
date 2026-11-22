"""Put the done line at the head of the A7 backlog item.

The token is the one done_check printed. The line is the one it asked for.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
HEAD = ("Done 2026-11-22. done_check deb8769e44. Verdicts: A7(1) rejected "
        "(results/2026-11-21_a7_reversal.json, 3781 names); A7(2) none kept "
        "of 92 cells (results/2026-11-22_a7_derivatives.json); A7(3) both "
        "pooled cells insufficient, survivor-biased "
        "(results/2026-11-22_a7_crowding.json); A7(4) insufficient at 1 day "
        "and rejected at 3 days, two names "
        "(results/2026-11-22_a7_funding.json). ")


def main():
    text = open(PATH).read()
    line = next(ln for ln in text.splitlines() if ln.startswith("- A7. "))
    if "done_check deb8769e44" in line:
        raise SystemExit("already written")
    updated = line.replace("- A7. ", "- A7. " + HEAD, 1)
    open(PATH, "w").write(text.replace(line, updated, 1))
    print("written")


if __name__ == "__main__":
    main()
