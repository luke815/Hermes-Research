"""Analogs, the paper track and the transitions for the risk dial.

The ten most recent dates in the same state, with the blend's return over
the next 10 and 30 days. The paper track starts the day the risk key first
existed and is the dial times the blend's realized return. A state change
is recorded with the date and the two states. The results file is written
by this script, and the same readings go into the risk key.
"""

import json
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from regime_tester.results_io import write_result  # noqa: E402
from regime_tester.risk import run_states  # noqa: E402
from dashboard_io import write_key  # noqa: E402

PANEL = os.path.join(ROOT, "data", "panel.csv")
KEY = os.path.join(ROOT, "dashboard", "keys", "risk.json")


def blend(panel):
    parts = (0.40 * panel["btc_price"].astype(float).pct_change()
             + 0.20 * panel["eth_price"].astype(float).pct_change()
             + 0.40 * panel["alt_price"].astype(float).pct_change())
    return (1 + parts.fillna(0)).cumprod()


def analogs(walked, prices, state, count=10):
    same = walked.index[walked["state"] == state]
    rows = []
    for stamp in reversed(list(same)):
        if stamp == walked.index[-1]:
            continue
        at = prices.index.get_loc(stamp)
        row = {"date": pd.Timestamp(stamp).strftime("%Y-%m-%d"), "state": state}
        for horizon, name in ((10, "fwd_10"), (30, "fwd_30")):
            end = at + horizon
            row[name] = (None if end >= len(prices)
                         else round(float(prices.iloc[end] / prices.iloc[at] - 1), 4))
        rows.append(row)
        if len(rows) == count:
            break
    return rows


def transitions(states):
    rows = []
    previous = None
    for stamp, state in states.items():
        if previous is not None and state != previous:
            rows.append({"date": pd.Timestamp(stamp).strftime("%Y-%m-%d"),
                         "from": previous, "to": state})
        previous = state
    return rows


def main():
    panel = pd.read_csv(PANEL, index_col=0, parse_dates=True)
    panel.index = pd.to_datetime(panel.index, utc=True)
    panel = panel.dropna(subset=["btc_price"])
    walked = run_states(panel)
    prices = blend(panel)
    state = walked["state"].iloc[-1]
    found = analogs(walked, prices, state)
    changes = transitions(walked["state"])
    key = json.loads(open(KEY).read())
    since = key.get("as_of")
    paper_return = None
    hold_return = None
    if since:
        stamp = pd.Timestamp(since, tz="UTC")
        if stamp in prices.index and stamp in walked.index:
            after = prices.loc[stamp:]
            held = walked["dial"].reindex(after.index).shift(1).fillna(walked["dial"].loc[stamp])
            change = after.pct_change().fillna(0)
            paper_return = round(float(((1 + held * change).prod()) - 1), 4)
            hold_return = round(float(after.iloc[-1] / after.iloc[0] - 1), 4)
    key["analogs"] = found
    key["transitions"] = changes[-10:]
    key["paper"] = {"since": since, "return": paper_return, "hold_return": hold_return}
    write_key(KEY, key)
    payload = {
        "item": "R5",
        "as_of": key.get("as_of"),
        "state": state,
        "analogs": found,
        "analog_count": len(found),
        "transitions": len(changes),
        "last_transition": changes[-1] if changes else None,
        "paper": key["paper"],
    }
    path = write_result("r5_live", payload, inputs=["data/panel.csv"])
    print(path)
    print(len(found), len(changes), key["paper"])


if __name__ == "__main__":
    main()
