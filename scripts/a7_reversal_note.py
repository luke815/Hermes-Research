"""Record why the A7(1) reversal score is not a verdict.

scripts/score_a7_reversal.py wrote results/2026-11-20_a7_reversal.json and
called the book rejected. The 3-day window at the 3-day horizon reports an
83 percent test spread, and scripts/a7_outlier.py traced it to one name.
This script reads both results files and the panel file that name came from,
and writes the cause. It does not rescore and it does not pull.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCORE = ROOT / "results" / "2026-11-20_a7_reversal.json"
OUTLIER = ROOT / "results" / "2026-11-20_a7_reversal_outlier.json"
PANEL = ROOT / "data" / "panel_xs_laevitas" / "binance_1000PEPEUSDT.csv"


def main():
    score = json.loads(SCORE.read_text())
    outlier = json.loads(OUTLIER.read_text())
    worst = outlier["worst"][0]
    lines = PANEL.read_text().splitlines()
    header = lines[0].split(",")
    close_at = header.index("close")
    rows = [line.split(",") for line in lines[1:] if line.startswith("2026-01-1")]
    closes = {row[0]: float(row[close_at]) for row in rows}
    payload = {
        "candidate": "a7_reversal",
        "score_file": "results/2026-11-20_a7_reversal.json",
        "score_verdict": score["verdict"],
        "score_verdicts": score["verdicts"],
        "w3_h3_test_spread_net": score["cells"][11]["summary"]["test"]["spread_net"],
        "cause": "one bad close",
        "file": "data/panel_xs_laevitas/binance_1000PEPEUSDT.csv",
        "name": worst["name"],
        "date": worst["date"],
        "contribution_pct": worst["spread_from_top"],
        "closes": closes,
        "verdict": "not a verdict",
        "reason": (
            "binance_1000PEPEUSDT closed at 0.005731 on 2026-01-13 against "
            "0.000006 on 2026-01-12 and 0.000007 on 2026-01-14. The longest "
            "file wins, so that one print is the PEPE column, and it is the "
            "whole 3-day test spread. The score stands as a reading of the "
            "panel as stored. It is not a verdict until that print is corrected."
        ),
    }
    path = write_result("a7_reversal_note", payload, inputs=[
        "results/2026-11-20_a7_reversal.json",
        "results/2026-11-20_a7_reversal_outlier.json",
        "data/panel_xs_laevitas/binance_1000PEPEUSDT.csv",
    ])
    print(path)


if __name__ == "__main__":
    main()
