"""Write the point-in-time universe and the long-short cost check.

Reads the span files, counts delisted names per date, and scores one long and
one short so the spread's net can be compared with its gross. Both numbers
come from this script.
"""

import json
import os
import sys
from datetime import datetime, timezone

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.costs import apply_costs  # noqa: E402
from regime_tester.pit import delisted_by_date, span_rows  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    universe = span_rows()
    counts = delisted_by_date(universe)
    out_dir = os.path.join(ROOT, "data")
    universe.to_csv(os.path.join(out_dir, "universe_pit.csv"), index=False)
    present = counts[counts["delisted_names"] > 0]
    present.to_csv(os.path.join(out_dir, "delisted_by_date.csv"), index=False)

    idx = pd.date_range("2024-01-01", periods=3, freq="D", tz="UTC")
    long_px = pd.Series([100.0, 101.0, 102.0], index=idx)
    short_px = pd.Series([100.0, 99.0, 98.0], index=idx)
    funding = pd.Series([0.01, 0.01, 0.01], index=idx)
    oi = pd.Series([60_000_000.0, 60_000_000.0, 60_000_000.0], index=idx)
    long = apply_costs(long_px, 1, 1, funding, oi)
    short = apply_costs(short_px, 1, -1, funding, oi)
    gross = float(long["gross"].iloc[0] + short["gross"].iloc[0])
    net = float(long["net"].iloc[0] + short["net"].iloc[0])

    by_exchange = universe.groupby("exchange")["delisted"].sum().astype(int).to_dict()
    result = {
        "as_of": today,
        "written_by": "scripts/a4_pit.py",
        "rows": int(len(universe)),
        "delisted": int(universe["delisted"].sum()),
        "delisted_by_exchange": by_exchange,
        "dates_with_delisted_names": int(len(present)),
        "delisted_names_file": "data/delisted_by_date.csv",
        "sample_dates": present.iloc[:: max(len(present) // 5, 1)].head(6).to_dict("records"),
        "costs": {
            "shape": "long plus short, horizon 1",
            "gross": round(gross, 6),
            "net": round(net, 6),
            "net_differs_from_gross": abs(net - gross) > 1e-9,
        },
    }
    path = os.path.join(ROOT, "results", f"{today}_a4_pit.json")
    json.dump(result, open(path, "w"), indent=1)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
