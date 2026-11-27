"""R1 inputs and the R2 dial, written by the script that computed them.

regime_tester.risk already computes both. build_risk.py writes them under
the e5 name, which is not the file this item's clause names. This script
computes the same reading and stamps it as r1 and as r2. It does not pull.
"""

import os
import sys

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from regime_tester.derivatives import market_measures  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402
from regime_tester.risk import latest, readings, run_states  # noqa: E402

PANEL = os.path.join(ROOT, "data", "panel.csv")


def _reading():
    panel = pd.read_csv(PANEL, index_col=0, parse_dates=True)
    panel.index = pd.to_datetime(panel.index, utc=True)
    market = market_measures()
    frame = readings(panel, market)
    walked = run_states(frame)
    return panel, frame, walked, latest(frame)


def score_r1():
    panel, frame, walked, reading = _reading()
    inputs = reading["inputs"]
    return {
        "item": "R1",
        "as_of": reading["as_of"],
        "panel_rows": int(len(panel)),
        "reading_rows": int(len(frame)),
        "inputs": inputs,
        "n_inputs": len(inputs),
        "unavailable": [row["name"] for row in inputs if not row["available"]],
        "verdict": "recorded",
        "reason": "the inputs are computed; several series are not on disk and stay unavailable",
    }


def score_r2():
    panel, frame, walked, reading = _reading()
    changes = int((walked["state"] != walked["state"].shift(1)).sum())
    return {
        "item": "R2",
        "as_of": reading["as_of"],
        "state": reading["state"],
        "dial": reading["dial"],
        "days_in_state": reading["days_in_state"],
        "changed_on": reading["changed_on"],
        "rules_fired": reading["rules_fired"],
        "vol_scalar": reading["vol_scalar"],
        "emergency_cut": reading["emergency_cut"],
        "state_changes": changes,
        "states_seen": sorted(set(walked["state"].dropna())),
        "verdict": "recorded",
        "reason": "the dial is the state machine's reading; it is not an admission",
    }


def main():
    r1 = score_r1()
    path = write_result("l6_r1", r1, inputs=["data/panel.csv", "data/laevitas/market"])
    print(path, r1["n_inputs"], len(r1["unavailable"]))
    r2 = score_r2()
    path = write_result("l6_r2", r2, inputs=["data/panel.csv", "data/laevitas/market"])
    print(path, r2["state"], r2["dial"], r2["state_changes"])


if __name__ == "__main__":
    main()
