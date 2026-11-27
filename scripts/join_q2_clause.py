"""Join Q2's continuation lines onto its item line.

done_check reads only the line that starts with '- Q2.'. The Done-when
clause sits on the continuation lines, so the checker sees no clause.
This joins those lines onto the item line and changes no word of them.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")


def main():
    lines = open(PATH).read().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("- Q2. "))
    end = start + 1
    while end < len(lines) and lines[end].startswith("  "):
        end += 1
    joined = " ".join(line.strip() for line in lines[start:end])
    if "Done when" not in joined:
        raise SystemExit("the joined line has no Done-when clause")
    if not joined.endswith("."):
        raise SystemExit("the joined line does not end a sentence")
    lines[start:end] = [joined]
    open(PATH, "w").write("\n".join(lines) + "\n")
    print(f"joined {end - start} lines into line {start + 1}, {len(joined)} chars")


if __name__ == "__main__":
    main()
