"""Run the exposure harness on the panel and record that it ran.

The clause needs the harness in regime_tester/strategy.py and a results
file written by the script that ran it. This runs buy and hold and the
200-day rule on the BTC close in data/panel.csv and writes the counts.
It does not score the dial; that is R4.
"""

import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from regime_tester.results_io import write_result  # noqa: E402
from regime_tester.strategy import buy_and_hold, rule_200d  # noqa: E402

PANEL = os.path.join(ROOT, "data", "panel.csv")


def main():
    panel = pd.read_csv(PANEL, index_col=0, parse_dates=True)
    panel.index = pd.to_datetime(panel.index, utc=True)
    close = panel["btc_price"].astype(float).dropna()
    funding = panel["funding"].astype(float).reindex(close.index) if "funding" in panel else None
    held = buy_and_hold(close, funding)
    rule = rule_200d(close, funding)
    payload = {
        "item": "R3",
        "panel_rows": int(len(close)),
        "first": close.index[0].strftime("%Y-%m-%d"),
        "last": close.index[-1].strftime("%Y-%m-%d"),
        "buy_and_hold_days": int(held["net"].notna().sum()),
        "buy_and_hold_opening_cost": float(held["cost"].iloc[0]),
        "buy_and_hold_later_costs": int((held["cost"].iloc[1:] > 0).sum()),
        "rule_200d_long_days": int((rule["gross"] > 0).sum()),
        "rule_200d_flat_days": int((rule["gross"] == 0).sum()),
        "funding_days": int(funding.notna().sum()) if funding is not None else 0,
    }
    path = write_result("r3_harness", payload, inputs=["data/panel.csv"])
    print(path)
    print(payload["buy_and_hold_days"], payload["rule_200d_long_days"])


if __name__ == "__main__":
    main()
