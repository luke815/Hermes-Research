"""Join Q1's split lines into one backlog line.

done_check reads one line per item, and Q1's Done-when clause sits on the
lines after the item header, so the check sees no clause. This joins the
continuation lines onto the header and changes nothing else.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
HEADER = "- Q1. "


def main():
    lines = open(PATH).read().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(HEADER))
    end = start + 1
    while end < len(lines) and not lines[end].startswith("- ") and lines[end].strip():
        end += 1
    joined = " ".join(line.strip() for line in lines[start:end])
    if "Done when" not in joined:
        raise SystemExit("joined line has no Done-when clause")
    if joined.count("Done when") != 1:
        raise SystemExit("joined line has more than one Done-when clause")
    out = lines[:start] + [joined] + lines[end:]
    open(PATH, "w").write("\n".join(out) + "\n")
    print(f"joined lines {start + 1} to {end} into one line of {len(joined)} chars")


if __name__ == "__main__":
    main()
