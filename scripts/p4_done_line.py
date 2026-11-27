"""Paste the done_check line onto the P4 item, exactly as printed."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
TOKEN = "Done 2026-11-20. done_check b0f61990e3."


def main():
    lines = open(PATH).read().splitlines()
    item = next(i for i, line in enumerate(lines) if line.startswith("- P4. "))
    if TOKEN in lines[item]:
        raise SystemExit("done line already present")
    lines[item] = lines[item].rstrip() + " " + TOKEN
    open(PATH, "w").write("\n".join(lines) + "\n")
    print("pasted")


if __name__ == "__main__":
    main()
