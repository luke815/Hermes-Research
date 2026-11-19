"""Paste the done_check line onto L10, exactly as printed."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
MARKER = "- L10."
LINE = "Done 2026-11-19. done_check cf900ecef5."


def main():
    lines = open(PATH).read().split("\n")
    hits = [i for i, line in enumerate(lines) if line.startswith(MARKER)]
    if len(hits) != 1:
        raise SystemExit(f"{len(hits)} L10 lines")
    if LINE in lines[hits[0]]:
        raise SystemExit("already pasted")
    lines[hits[0]] = lines[hits[0]].rstrip() + " " + LINE
    open(PATH, "w").write("\n".join(lines))
    print("pasted")


if __name__ == "__main__":
    main()
