"""Move the P4 done-when clause onto one line, so the checker reads both parts."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
CLAUSE = ("Done when research/outside/PREREG4.md is committed before any cell "
          "is scored, and the results file written by write_result carries a "
          "verdict for A1, A2, A3 and A6 and the A5 transition matrix with no "
          "verdict.")


def main():
    lines = open(PATH).read().splitlines()
    item = next(i for i, line in enumerate(lines) if line.startswith("- P4. "))
    if CLAUSE in lines[item]:
        raise SystemExit("clause already on the item line")
    lines[item] = lines[item].rstrip() + " " + CLAUSE
    # The wrapped copy on the following lines would be a second clause.
    for i in range(item + 1, len(lines)):
        if lines[i].startswith("- ") or lines[i].startswith("## "):
            break
        if "Done when" in lines[i]:
            lines[i] = lines[i].split("Done when")[0].rstrip()
    open(PATH, "w").write("\n".join(lines) + "\n")
    print("moved")


if __name__ == "__main__":
    main()
