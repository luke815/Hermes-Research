"""Copy high and low onto the panel the sweep reads, where a file already has them.

data/panel_xs carries high and low for the Binance names the high_low daemon
filled. data/panel_xs_laevitas, which the sweep reads, carries none. A date is
copied only when both panels have that date, and a name whose file lacks the
columns is left as it is. The result is a sibling directory; data_guard swaps
it in. This script does not pull.
"""

import os
import shutil
import sys

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "panel_xs")
DST = os.path.join(ROOT, "data", "panel_xs_laevitas")
OUT = os.path.join(ROOT, "data", "panel_xs_laevitas_range")


def copy_range():
    if os.path.exists(OUT):
        raise SystemExit(f"{OUT} already exists")
    os.makedirs(OUT)
    copied = 0
    dates = 0
    skipped = 0
    for name in sorted(os.listdir(DST)):
        if not name.endswith(".csv"):
            continue
        target = os.path.join(DST, name)
        source = os.path.join(SRC, name)
        if not os.path.exists(source):
            shutil.copy2(target, os.path.join(OUT, name))
            skipped += 1
            continue
        donor = pd.read_csv(source, usecols=lambda c: c in ("date", "high", "low"))
        if "high" not in donor.columns or "low" not in donor.columns:
            shutil.copy2(target, os.path.join(OUT, name))
            skipped += 1
            continue
        donor = donor.dropna(subset=["high", "low"]).drop_duplicates("date")
        if donor.empty:
            shutil.copy2(target, os.path.join(OUT, name))
            skipped += 1
            continue
        frame = pd.read_csv(target)
        if "high" in frame.columns or "low" in frame.columns:
            raise SystemExit(f"{name} already carries a range column")
        merged = frame.merge(donor, on="date", how="left")
        filled = int(merged["high"].notna().sum())
        merged.to_csv(os.path.join(OUT, name), index=False)
        if filled:
            copied += 1
            dates += filled
        else:
            skipped += 1
    return {"files_with_range": copied, "dates_filled": dates,
            "files_unchanged": skipped, "out": OUT}


if __name__ == "__main__":
    print(copy_range())
