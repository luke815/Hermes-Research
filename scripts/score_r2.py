"""The R2 daily reading: state, dial and the rules that set it.

The state machine is regime_tester.risk, which follows
research/RISK_REGIME.md section 2. This script runs it on the panel the
R1 job wrote, keeps a state inside the five-day hysteresis unless a
capitulation flag is on, scales the dial by target vol over realized
vol, and writes the reading into the risk key beside the R1 inputs. The
scheduler runs it daily. The results file is written by this script.
"""

import json
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from regime_tester.results_io import write_result  # noqa: E402
from regime_tester.risk import days_in_state, run_states, vol_scalar_of  # noqa: E402
from dashboard_io import write_key  # noqa: E402

PANEL = os.path.join(ROOT, "data", "panel.csv")
KEY = os.path.join(ROOT, "dashboard", "keys", "risk.json")


def _clean(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (bool,)):
        return bool(value)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value
    return None if pd.isna(number) else number


def main():
    panel = pd.read_csv(PANEL, index_col=0, parse_dates=True)
    panel.index = pd.to_datetime(panel.index, utc=True)
    panel = panel.dropna(subset=["btc_price"])
    breadth = None
    if "breadth_above_50d" in panel.columns:
        breadth = panel["breadth_above_50d"].astype(float)
    walked = run_states(panel, breadth)
    last = walked.index[-1]
    held, changed = days_in_state(walked["state"])
    reading = {k: _clean(v) for k, v in panel.loc[last].items()}
    scalar = vol_scalar_of(reading.get("rv_pct"), reading.get("rv_30"))
    key = json.loads(open(KEY).read()) if os.path.exists(KEY) else {}
    key.update({
        "as_of": last.strftime("%Y-%m-%d"),
        "state": walked["state"].iloc[-1],
        "dial": float(walked["dial"].iloc[-1]),
        "days_in_state": held,
        "changed_on": changed,
        "rules_fired": list(walked["rules"].iloc[-1]),
        "vol_scalar": round(float(scalar), 4),
        "emergency_cut": bool(walked["emergency_cut"].iloc[-1]),
        "status": "provisional",
    })
    write_key(KEY, key)
    scheduler = open(os.path.join(ROOT, "scripts", "scheduler.py")).read()
    slot = '"name": "risk_state", "at": "06:50", "script": "scripts/score_r2.py"'
    payload = {
        "item": "R2",
        "as_of": key["as_of"],
        "scheduler_slot": slot in scheduler,
        "state": key["state"],
        "dial": key["dial"],
        "days_in_state": key["days_in_state"],
        "changed_on": key["changed_on"],
        "rules_fired": key["rules_fired"],
        "vol_scalar": key["vol_scalar"],
        "emergency_cut": key["emergency_cut"],
        "panel_rows": int(len(panel)),
        "breadth_used": breadth is not None,
    }
    path = write_result("r2_state", payload, inputs=["data/panel.csv"])
    print(path)
    print(json.dumps({k: payload[k] for k in (
        "as_of", "state", "dial", "rules_fired", "vol_scalar")}))


if __name__ == "__main__":
    main()
