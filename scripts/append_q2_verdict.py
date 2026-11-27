"""Record the Q2 reading on its backlog line.

The numbers come from results/2026-11-20_q2_skew_no_vol.json, written by
scripts/score_q2.py. This script only records the reading.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "research", "backlog.md")
RESULT = os.path.join(ROOT, "results", "2026-11-20_q2_skew_no_vol.json")
ANCHOR = ("Done when results/<date>_q2_skew_no_vol.json shows\n"
          "  the two fresh windows separately and the pre-registration commit "
          "precedes the scoring commit.")


def main():
    reading = json.load(open(RESULT))
    if reading["provenance"]["commit"] == reading["prereg_commit"]:
        raise SystemExit("the scoring commit is the pre-registration commit")
    cells = reading["cells"]
    if any(cell["verdict"] != "insufficient" for cell in cells):
        raise SystemExit("a cell is not insufficient; this note records that reading")
    btc = next(cell for cell in cells
               if cell["asset"] == "BTC" and cell["target"] == "return"
               and cell["horizon"] == 5)
    early = btc["fresh"][0]
    late = btc["fresh"][1]
    text = open(PATH).read()
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {text.count(ANCHOR)}")
    note = (
        " Scored 2026-11-20 14:17 UTC: results/2026-11-20_q2_skew_no_vol.json "
        f"shows the two fresh windows separately, pre-registration "
        f"{reading['prereg_commit'][:10]} before the scoring commit "
        f"{reading['provenance']['commit'][:10]}, lookahead passed. All 10 "
        "cells are insufficient. The 2019-03 to 2020-01 window has "
        f"{early['n']} days because dvol starts 2021-03-25, and the 2026 "
        f"window has {late['episodes']} episodes on BTC and 10 on ETH against "
        "a bar of 20."
    )
    open(PATH, "w").write(text.replace(ANCHOR, ANCHOR + note, 1))
    print("appended")


if __name__ == "__main__":
    main()
