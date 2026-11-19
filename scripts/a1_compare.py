"""Compare panel_xs with the rewritten panel_xs_sum2, file by file.

Counts date loss, row loss and funding-column changes. Writes nothing to the
panel. Prints a JSON summary.
"""

import json
import os
import sys
from glob import glob

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "panel_xs")
DST = os.path.join(ROOT, "data", "panel_xs_sum2")


def main():
    names = sorted(os.path.basename(p) for p in glob(os.path.join(SRC, "*.csv")))
    date_loss, row_loss = [], []
    funding_added = funding_removed = shrunk = shrunk_no_loss = 0
    lost_dates_sample = []
    for name in names:
        sa = os.path.getsize(os.path.join(SRC, name))
        sb = os.path.getsize(os.path.join(DST, name))
        a = pd.read_csv(os.path.join(SRC, name))
        b = pd.read_csv(os.path.join(DST, name))
        ad = set(a["date"].astype(str).str.slice(0, 10)) if "date" in a.columns else set()
        bd = set(b["date"].astype(str).str.slice(0, 10)) if "date" in b.columns else set()
        lost = sorted(ad - bd)
        if lost:
            date_loss.append(name)
            if len(lost_dates_sample) < 6:
                lost_dates_sample.append({"name": name, "lost": len(lost),
                                          "first": lost[:2], "last": lost[-2:]})
        if len(b) < len(a):
            row_loss.append({"name": name, "before": len(a), "after": len(b)})
        if "funding_rate" in b.columns and "funding_rate" not in a.columns:
            funding_added += 1
        if "funding_rate" not in b.columns and "funding_rate" in a.columns:
            funding_removed += 1
        if sb < sa:
            shrunk += 1
            if not lost and len(b) >= len(a):
                shrunk_no_loss += 1
    out = {
        "names": len(names),
        "date_loss_files": len(date_loss),
        "row_loss_files": len(row_loss),
        "row_loss_sample": row_loss[:6],
        "funding_added": funding_added,
        "funding_removed": funding_removed,
        "shrunk_files": shrunk,
        "shrunk_with_no_row_or_date_loss": shrunk_no_loss,
        "lost_dates_sample": lost_dates_sample,
    }
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
