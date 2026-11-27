"""The positioning watch card, read from the Q1 results file.

The card used to quote the two-asset base rate from the 2026-11-18 pass.
The clause says it reads the scored file instead. This writes only
dashboard/keys/q1.json. The assembler merges it; this script does not.
"""

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dashboard_io import write_key  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "dashboard", "keys", "q1.json")


def latest(directory):
    """The newest Q1 results file, by the date in its name."""
    found = sorted(glob.glob(os.path.join(directory, "*_q1_lsr_drawdown.json")))
    if not found:
        raise SystemExit("no Q1 results file")
    return found[-1]


def card(reading, source):
    """One row per window, validation numbers, the verdict the scorer wrote."""
    windows = []
    for cell in reading["cells"]:
        validation = cell["periods"]["validation"]
        windows.append({
            "asset": cell["asset"],
            "window": cell["window"],
            "drawdown_effect": validation.get("drawdown_effect"),
            "crash_lift": validation.get("crash_lift"),
            "false_alarm": validation.get("false_alarm"),
            "episodes_train_validation": (
                cell["episodes"]["train"] + cell["episodes"]["validation"]),
            "verdict": cell["verdict"],
        })
    verdicts = {row["verdict"] for row in windows}
    return {
        "source": os.path.basename(source),
        "names": reading["pooled_names"],
        "status": "insufficient" if "insufficient" in verdicts else "scored",
        "windows": windows,
        "note": (
            "Validation numbers from the scored file. A window below 20 "
            "episodes across train and validation is insufficient, not a signal."
        ),
    }


def main():
    source = latest(os.path.join(ROOT, "results"))
    reading = json.load(open(source))
    write_key(OUT, card(reading, source))
    print(OUT)


if __name__ == "__main__":
    main()
