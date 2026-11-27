"""Join Q6's verdict onto its item line.

The verdict sits on the line after the header, so the stall check, which
only reads the header line, treats a rejected item as open. This joins the
continuation lines and changes no word.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")


def main():
    lines = open(PATH).read().splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("- Q6. "))
    end = start + 1
    while end < len(lines) and not lines[end].startswith("- ") and not lines[end].startswith("#"):
        end += 1
    joined = " ".join(ln.strip() for ln in lines[start:end])
    if "Verdict 2026-11-21: rejected." not in joined:
        raise SystemExit("verdict not on the continuation lines")
    lines[start:end] = [joined]
    open(PATH, "w").write("\n".join(lines) + "\n")
    print(f"joined {end - start} lines")


if __name__ == "__main__":
    main()
