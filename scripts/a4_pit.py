"""A4. Count the delisted names present on each date, and the long-short cost.

Reads the span files and writes how many delisted names are still inside
their span on each date. Then scores one long and one short so the spread's
net can be compared with its gross: both legs pay a round trip, and the long
pays the carry the short receives. Both numbers come from this script.
"""

import os
import sys
from datetime import datetime, timezone

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.costs import apply_costs  # noqa: E402
from regime_tester.pit import delisted_by_date, span_rows  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    universe = span_rows()
    counts = delisted_by_date(universe)
    present = counts[counts["delisted_names"] > 0]

    idx = pd.date_range("2024-01-01", periods=3, freq="D", tz="UTC")
    long_px = pd.Series([100.0, 101.0, 102.0], index=idx)
    short_px = pd.Series([100.0, 99.0, 98.0], index=idx)
    funding = pd.Series([0.01, 0.01, 0.01], index=idx)
    oi = pd.Series([60_000_000.0, 60_000_000.0, 60_000_000.0], index=idx)
    long = apply_costs(long_px, 1, 1, funding, oi)
    short = apply_costs(short_px, 1, -1, funding, oi)
    at = 0
    gross = float(long["gross"].iloc[at] + short["gross"].iloc[at])
    net = float(long["net"].iloc[at] + short["net"].iloc[at])
    both_legs = float(long["round_trip"].iloc[at] + short["round_trip"].iloc[at])
    both_carry = float(long["carry"].iloc[at] + short["carry"].iloc[at])

    by_exchange = {k: int(v) for k, v in universe.groupby("exchange")["delisted"].sum().items()}
    payload = {
        "as_of": today,
        "rows": int(len(universe)),
        "delisted": int(universe["delisted"].sum()),
        "delisted_by_exchange": by_exchange,
        "dates_with_delisted_names": int(len(present)),
        "delisted_names_min": int(present["delisted_names"].min()) if len(present) else 0,
        "delisted_names_max": int(present["delisted_names"].max()) if len(present) else 0,
        "costs": {
            "shape": "long plus short, horizon 1",
            "gross": round(gross, 6),
            "net": round(net, 6),
            "both_legs_round_trip": round(both_legs, 6),
            "both_sides_carry": round(both_carry, 6),
            "net_differs_from_gross": abs(net - gross) > 1e-9,
            "gap_equals_both_legs_and_carry": abs((gross - net) - (both_legs + both_carry)) < 1e-9,
        },
    }
    path = write_result("a4_pit", payload, inputs=["data/binance_span.csv",
                                                    "data/bybit_span.csv",
                                                    "data/okx_span.csv"])
    print(path)


if __name__ == "__main__":
    main()
