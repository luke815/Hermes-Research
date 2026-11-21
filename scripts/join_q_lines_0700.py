"""Join a split backlog item onto the line that starts with its header.

The stall check only reads the header line, so a verdict or a block written
on the following lines is invisible and the item stays the top item forever.
This joins the continuation lines of Q3, Q4 and Q5 onto their header lines.
It changes no word.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
ITEMS = ("- Q3. ", "- Q4. ", "- Q5. ")


def main():
    lines = open(PATH).read().splitlines()
    joined = 0
    i = 0
    out = []
    while i < len(lines):
        if any(lines[i].startswith(item) for item in ITEMS):
            end = i + 1
            while end < len(lines) and not lines[end].startswith("- ") and not lines[end].startswith("#"):
                end += 1
            out.append(" ".join(ln.strip() for ln in lines[i:end]))
            joined += end - i
            i = end
            continue
        out.append(lines[i])
        i += 1
    open(PATH, "w").write("\n".join(out) + "\n")
    print(f"joined {joined} lines")


if __name__ == "__main__":
    main()
