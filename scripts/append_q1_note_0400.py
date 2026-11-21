"""Record this run's reading of Q1 on its backlog line.

The hosted page now carries the q1 key. The claim is still live and held by a
dead process, and a research run does not steal a live claim, so this script
only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
HOSTED = "/tmp/hosted_data.json"
ANCHOR = "Unblocks when that hosted file carries the q1 key."


def main():
    hosted = json.load(open(HOSTED))
    q1 = hosted.get("q1")
    if not q1:
        raise SystemExit("hosted page has no q1 key")
    text = open(PATH).read()
    marker = "Rechecked 2026-11-21 04:00 UTC: the hosted page"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- Q1. "))
    if ANCHOR not in line:
        raise SystemExit("anchor missing from the Q1 line")
    note = (
        " Rechecked 2026-11-21 04:00 UTC: the hosted page at "
        "https://luke815.github.io/Hermes-Dashboard-1/data.json now carries "
        f"the q1 key, generated_at {hosted.get('generated_at')}, source "
        f"{q1.get('source')}, {len(q1.get('windows', []))} windows. "
        "ops/claims/Q1.json is still a live claim by cron, taken "
        "2026-11-21T01:06:10Z with ttl 6h, and the holder pid 6894 is dead. A "
        "research run does not steal a live claim. Unblocks when the claim "
        "expires at 2026-11-21T07:06:10Z or the holder releases it."
    )
    updated = line.replace(ANCHOR, ANCHOR + note, 1)
    open(PATH, "w").write(text.replace(line, updated, 1))
    print("appended")


if __name__ == "__main__":
    main()
