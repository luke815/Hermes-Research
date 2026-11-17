"""Rewrite panel_xs from the daily funding sum, into a new directory.

The funding stores keep the last settlement or the day's mean. The sum lives
in data/funding_sum/, one file per name, written by scripts/funding_sum.py
and scripts/okx_funding_sum.py. A name with no sum file keeps its prices and
loses its funding column, because a last print is not the day's funding and
writing it would repeat the bug.

Every file is sorted, de-duplicated and cut before today, since a bar is
stamped with its open time and today's bar has not closed. The rewrite goes
to data/panel_xs_sum/ and is compared before anything replaces panel_xs.

Writes results/<today>_a1_integrity.json itself.
"""

import json
import os
import sys
from datetime import datetime, timezone
from glob import glob

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.panel_integrity import base_of, clean_frame  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs")
DEST = os.path.join(ROOT, "data", "panel_xs_sum")
SUMS = os.path.join(ROOT, "data", "funding_sum")
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# The archive walk stores stopped OKX names under okx_archive_. The paged
# pull stores live names under okx_. A name uses the archive file when it
# exists, because that one reaches back to 2021.
SUM_PREFIX = {"binance": ["binance_"], "bybit": ["bybit_"], "okx": ["okx_archive_", "okx_"]}


def sum_frame(exchange, symbol):
    """The daily sum for one name, or None when no sum has been pulled."""
    for prefix in SUM_PREFIX.get(exchange, []):
        path = os.path.join(SUMS, f"{prefix}{symbol}.csv")
        if os.path.exists(path) and os.path.getsize(path) > 40:
            frame = pd.read_csv(path)
            frame["date"] = frame["date"].astype(str).str.slice(0, 10)
            return frame.set_index("date")[["funding_rate", "funding_count",
                                            "funding_interval_hours"]]
    return None


def rewrite():
    """Write every panel file to DEST, funded from the sum where one exists."""
    os.makedirs(DEST, exist_ok=True)
    funded, unfunded, future_dropped = [], [], 0
    for path in sorted(glob(os.path.join(PANEL, "*.csv"))):
        name = os.path.basename(path)
        exchange, symbol = name.split("_", 1)
        symbol = symbol[:-4]
        frame = pd.read_csv(path)
        before = set(frame["date"].astype(str).str.slice(0, 10)) if "date" in frame.columns else set()
        summed = sum_frame(exchange, symbol)
        if summed is not None and "date" in frame.columns:
            frame = frame.drop(columns=[c for c in
                                        ("funding_rate", "funding_count", "funding_interval_hours")
                                        if c in frame.columns])
            frame = frame.merge(summed, left_on="date", right_index=True, how="left")
            funded.append(name)
        else:
            frame = frame.drop(columns=[c for c in ("funding_rate",) if c in frame.columns])
            unfunded.append(name)
        cleaned = clean_frame(frame, today=TODAY)
        after = set(cleaned["date"].astype(str)) if "date" in cleaned.columns else set()
        future_dropped += len(before - after)
        tmp = os.path.join(DEST, name + ".tmp")
        cleaned.to_csv(tmp, index=False)
        os.replace(tmp, os.path.join(DEST, name))
    return funded, unfunded, future_dropped


def main():
    funded, unfunded, future_dropped = rewrite()
    out = {
        "date": TODAY,
        "written_by": "scripts/a1_rewrite.py",
        "dest": DEST,
        "files": len(funded) + len(unfunded),
        "funded_from_sum": len(funded),
        "funded_names": funded,
        "unfunded_no_sum_file": len(unfunded),
        "future_or_today_bars_dropped": future_dropped,
        "note": ("funding comes only from data/funding_sum, which sums the day's "
                 "settlements. A name with no sum file has its funding column removed "
                 "rather than keeping the last print. Today's open bar is dropped."),
    }
    dest = os.path.join(ROOT, "results", f"{TODAY}_a1_integrity.json")
    json.dump(out, open(dest, "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "funded_names"}))


if __name__ == "__main__":
    main()
