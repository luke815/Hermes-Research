"""Write the D2 units reading from the saved files.

The daily and hourly medians are read from the files the outside pull saved.
Nothing is fetched.
"""

import gzip
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DAILY = ROOT / "data" / "outside_laevitas" / "perp_funding_BTC_1d.csv.gz"
HOURLY = ROOT / "data" / "outside_laevitas" / "perp_funding_BTC_1h.csv.gz"


def median(path):
    import pandas as pd
    frame = pd.read_csv(path)
    values = pd.to_numeric(frame["value"], errors="coerce").dropna()
    return float(values.median()), int(len(values))


def main():
    daily, daily_n = median(DAILY)
    hourly, hourly_n = median(HOURLY)
    payload = {
        "candidate": "d2_funding_units",
        "daily_file": "data/outside_laevitas/perp_funding_BTC_1d.csv.gz",
        "daily_median": daily,
        "daily_n": daily_n,
        "hourly_file": "data/outside_laevitas/perp_funding_BTC_1h.csv.gz",
        "hourly_median": hourly,
        "hourly_n": hourly_n,
        "ratio": None if hourly == 0 else daily / hourly,
        "band": [0.001, 0.05],
        "daily_inside_band": 0.001 <= daily <= 0.05,
    }
    path = write_result("d2_funding_units", payload, inputs=[
        "data/outside_laevitas/perp_funding_BTC_1d.csv.gz",
        "data/outside_laevitas/perp_funding_BTC_1h.csv.gz",
    ])
    print(path)


if __name__ == "__main__":
    main()
