"""R5 analogs and the paper track, and R6 the weekly note.

Analogs are the ten most recent dates in the current state, and what BTC
did over the next 10 and 30 days from each. The paper track starts today,
so its return is zero until a later day. The weekly note lists the state
changes in the last seven days. This script writes both files. It does not
pull.
"""

import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from regime_tester.derivatives import market_measures  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402
from regime_tester.risk import readings, run_states  # noqa: E402

PANEL = os.path.join(ROOT, "data", "panel.csv")


def _walked():
    panel = pd.read_csv(PANEL, index_col=0, parse_dates=True)
    panel.index = pd.to_datetime(panel.index, utc=True)
    walked = run_states(readings(panel, market_measures()))
    close = panel["btc_price"].astype(float).reindex(walked.index)
    return walked, close


def score_r5():
    walked, close = _walked()
    state = walked["state"].iloc[-1]
    forward_10 = close.shift(-10) / close - 1
    forward_30 = close.shift(-30) / close - 1
    same = walked.index[walked["state"].eq(state)]
    analogs = []
    for stamp in reversed(list(same[:-1])):
        if len(analogs) >= 10:
            break
        analogs.append({
            "date": str(pd.Timestamp(stamp).date()),
            "state": state,
            "fwd_10": None if pd.isna(forward_10.loc[stamp]) else round(float(forward_10.loc[stamp]), 6),
            "fwd_30": None if pd.isna(forward_30.loc[stamp]) else round(float(forward_30.loc[stamp]), 6),
        })
    changes = walked["state"].ne(walked["state"].shift(1))
    transitions = []
    for stamp in walked.index[changes][-10:]:
        previous = walked["state"].shift(1).loc[stamp]
        transitions.append({
            "date": str(pd.Timestamp(stamp).date()),
            "from": None if pd.isna(previous) else previous,
            "to": walked["state"].loc[stamp],
        })
    return {
        "item": "R5",
        "as_of": str(walked.index[-1].date()),
        "state": state,
        "analogs": analogs,
        "n_analogs": len(analogs),
        "transitions": transitions,
        "paper": {"since": str(walked.index[-1].date()), "return": 0.0, "hold_return": 0.0},
        "verdict": "recorded",
        "reason": "analogs are the last ten dates in the current state; the paper track starts today",
    }


def score_r6():
    walked, close = _walked()
    end = walked.index[-1]
    week = walked.loc[walked.index >= end - pd.Timedelta(days=7)]
    changes = []
    previous = walked["state"].shift(1)
    for stamp in week.index:
        if previous.loc[stamp] != week["state"].loc[stamp] and pd.notna(previous.loc[stamp]):
            changes.append({
                "date": str(pd.Timestamp(stamp).date()),
                "from": previous.loc[stamp],
                "to": week["state"].loc[stamp],
            })
    return {
        "item": "R6",
        "as_of": str(end.date()),
        "week_start": str(week.index[0].date()),
        "state": walked["state"].iloc[-1],
        "state_changes": changes,
        "n_changes": len(changes),
        "verdict": "recorded",
        "reason": "the weekly note lists the state changes in the last seven days",
    }


def main():
    r5 = score_r5()
    path = write_result("l6_r5", r5, inputs=["data/panel.csv", "data/laevitas/market"])
    print(path, r5["n_analogs"])
    r6 = score_r6()
    path = write_result("l6_r6", r6, inputs=["data/panel.csv", "data/laevitas/market"])
    print(path, r6["n_changes"])


if __name__ == "__main__":
    main()
