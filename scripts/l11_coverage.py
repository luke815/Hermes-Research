"""Count funding, open interest and basis on the dead names from 2021.

L11's clause asks that A4's universe have those three series for the dead
names from 2021. The merge wrote the files; this reads them and writes the
counts. It does not pull and it does not decide the item is done.

Usage: python3 scripts/l11_coverage.py
"""

import csv
import os
import sys

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from delisted_pull import dead_names  # noqa: E402
from merge_delisted import panel_name  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs_laevitas")
FIELDS = ("funding_rate", "oi_usd", "basis")
FROM = "2021"


def coverage(today):
    """One row per dead name: whether each field has a value, and in 2021."""
    rows = []
    for dead in dead_names(today):
        saved = f"{dead['market']}_{dead['instrument']}.json"
        path = os.path.join(PANEL, panel_name(saved))
        row = {"market": dead["market"], "symbol": dead["symbol"],
               "file": os.path.basename(path), "present": os.path.exists(path)}
        if row["present"]:
            frame = pd.read_csv(path)
            row["first"] = str(frame["date"].iloc[0]) if len(frame) else None
            row["bars"] = int(len(frame))
            for field in FIELDS:
                values = frame[field].notna() if field in frame.columns else None
                row[field] = int(values.sum()) if values is not None else 0
                row[field + "_from_2021"] = bool(
                    values is not None and values.any()
                    and str(frame.loc[values, "date"].iloc[0])[:4] <= FROM)
        rows.append(row)
    return rows


def main():
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = coverage(today)
    present = [r for r in rows if r["present"]]
    out = {
        "item": "L11",
        "today": today,
        "dead_names": len(rows),
        "panel_files": len(present),
        "missing_file": len(rows) - len(present),
        "earliest_first_bar": min((r["first"] for r in present), default=None),
    }
    for field in FIELDS:
        have = [r for r in present if r.get(field)]
        early = [r for r in present if r.get(field + "_from_2021")]
        out[field] = {"names_with_values": len(have),
                      "names_from_2021": len(early),
                      "earliest": min((r["first"] for r in early), default=None)}
    out["all_three_from_2021"] = sum(
        1 for r in present
        if all(r.get(field + "_from_2021") for field in FIELDS))
    path = write_result("l11_coverage", out, inputs=[
        "data/panel_xs_laevitas", "data/binance_span.csv",
        "data/bybit_span.csv", "data/okx_span.csv"])
    print(path)


if __name__ == "__main__":
    main()
