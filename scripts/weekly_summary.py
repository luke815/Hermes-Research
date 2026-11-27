"""Assemble the weekly summary from the three cell files this script wrote.

The per-cell files are the source. This reads them and writes one summary
through write_result, so the note quotes one file. It computes nothing.
"""

import json
import os
import sys

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone  # noqa: E402

from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
CELLS = ("w25_ls_ratio_chg_7", "w26_basis_chg_7", "w27_wma_20")


def main():
    rows = []
    for name in CELLS:
        path = os.path.join(ROOT, "results", f"{TODAY}_{name}.json")
        rows.append(json.loads(open(path).read()))
    payload = {
        "job": "regime-weekly-research",
        "prereg_commit": "14e6cba8e0e0b9ab23050e1cfe19d2d9b1d6507c",
        "added": [],
        "dropped": [],
        "retested": [row["candidate"] for row in rows],
        "decisions": {row["candidate"]: row["verdict"] for row in rows},
        "candidates": rows,
        "panel_end": rows[-1]["panel_end"],
        "names": rows[-1]["names"],
    }
    path = write_result("regime-weekly-research", payload, inputs=[
        f"results/{TODAY}_{name}.json" for name in CELLS])
    print(path)


if __name__ == "__main__":
    main()
