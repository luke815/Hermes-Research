"""Record a blocked note or a result for any item.

One script, so a note does not need its own file. The payload comes from
arguments, which is a hand-written result by construction: a blocked note has
no computation behind it. A result that was computed belongs to the script
that computed it.

    python3 scripts/record_note.py L11 blocked "the catalogue has no delisted flag"
    python3 scripts/record_note.py L11 result results/2026-11-22_l11_coverage.json
"""

import json
import sys

from regime_tester.results_io import write_result


def main():
    item, kind, rest = sys.argv[1], sys.argv[2], sys.argv[3]
    if kind == "blocked":
        payload = {"item": item, "status": "blocked", "note": rest}
        name = f"{item.lower()}_blocked"
    elif kind == "result":
        payload = json.load(open(rest))
        payload.pop("provenance", None)
        name = rest.rsplit("/", 1)[-1][:-5]
    else:
        raise SystemExit(f"unknown kind {kind}")
    path = write_result(name, payload, inputs=[])
    print(path)


if __name__ == "__main__":
    main()
