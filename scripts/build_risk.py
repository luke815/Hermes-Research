"""Write the risk key from the panels and record the reading.

Computes the R1 inputs and the R2 dial for the last closed day and writes
only dashboard/keys/risk.json. The assembler merges and pushes. The results
file carries the same reading, written by this script, so the number in the
report is the number the key holds.
"""

import json
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from regime_tester.derivatives import market_measures  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402
from regime_tester.risk import latest, readings  # noqa: E402
from dashboard_io import write_key  # noqa: E402

PANEL = os.path.join(ROOT, "data", "panel.csv")
OUT = os.path.join(ROOT, "dashboard", "keys", "risk.json")


def build():
    panel = pd.read_csv(PANEL, index_col=0, parse_dates=True)
    panel.index = pd.to_datetime(panel.index, utc=True)
    market = market_measures()
    frame = readings(panel, market)
    reading = latest(frame)
    reading["backtest"] = {"status": "pending", "by_year": [], "variants": []}
    reading["analogs"] = []
    reading["transitions"] = []
    reading["paper"] = {"since": reading["as_of"], "return": 0.0, "hold_return": 0.0}
    reading["series"] = {"date": [], "dial": [], "state": []}
    reading["breadth"] = "unavailable"
    reading["note"] = ("Provisional. Breadth, open interest, liquidations and the macro "
                       "series are not on disk, so those inputs are unavailable and their "
                       "rules do not fire. The backtest is pending.")
    return reading


def main():
    reading = build()
    write_key(OUT, reading)
    payload = {
        "as_of": reading["as_of"],
        "state": reading["state"],
        "dial": reading["dial"],
        "days_in_state": reading["days_in_state"],
        "changed_on": reading["changed_on"],
        "rules_fired": reading["rules_fired"],
        "vol_scalar": reading["vol_scalar"],
        "emergency_cut": reading["emergency_cut"],
        "inputs": reading["inputs"],
        "unavailable": [row["name"] for row in reading["inputs"] if not row["available"]],
        "backtest_status": "pending",
    }
    path = write_result("e5_risk", payload, inputs=["data/panel.csv", "data/laevitas/market"])
    print(json.dumps({"results": path, "as_of": payload["as_of"], "state": payload["state"],
                      "dial": payload["dial"], "unavailable": len(payload["unavailable"])}))


if __name__ == "__main__":
    main()
