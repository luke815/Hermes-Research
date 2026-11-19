"""Write the E4 done line exactly as done_check printed it."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
ANCHOR = "Done when the hosted key has cells with names and the shadow file exists."
LINE = " Done 2026-11-19. done_check cd95963b2f."


def main():
    text = open(BACKLOG).read()
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    if LINE.strip() in text:
        raise SystemExit("done line already present")
    open(BACKLOG, "w").write(text.replace(ANCHOR, ANCHOR + LINE, 1))
    print("backlog updated", os.path.getsize(BACKLOG))


if __name__ == "__main__":
    main()
