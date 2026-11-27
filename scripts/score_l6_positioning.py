"""Record the L6 positioning verdict from the sweep's own rows.

The four series are funding, open interest, basis and the long/short ratio.
Open interest has no change column, so the measure that uses it is
oi_on_down_days. The cross-section sweep already scored these measures on the
current liquid universe and wrote the rows. Recomputing them does not finish
inside a research run, and a second copy of the same spread would not be a
new test. This script reads those rows, on the current name count only, and
marks a cell usable only with 40 non-overlapping observations and a non-zero
spread. A row from an older universe is dropped. Admission waits on
validation and test, which this script does not read. It writes the results
file. It does not pull and it does not confirm.
"""

import glob
import os
import sys

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from regime_tester.results_io import write_result  # noqa: E402
import sweep_xs  # noqa: E402

MEASURES = ("funding_persist_high", "oi_on_down_days", "basis_level", "ls_ratio_level")
MIN_INDEPENDENT = 40
SWEEPS = os.path.join(ROOT, "results", "sweeps")


def mark_usable(row):
    """A cell is usable only with 40 independent observations and a real spread.

    A NaN spread and a zero spread are both unusable. The count is the
    non-overlapping one the sweep already computed.
    """
    n_ind = int(row["n_independent"])
    spread = row["spread"]
    sign = 0.0
    if spread == spread and spread is not None:
        sign = float(np.sign(spread))
    row["usable"] = bool(n_ind >= MIN_INDEPENDENT and sign != 0.0)
    return row


def current_rows():
    """Positioning rows scored on the universe load_train returns now.

    A row whose name count differs was scored on an older universe and does
    not count. The files are the sweep's own output.
    """
    close, digest = sweep_xs.load_train()
    names = int(close.shape[1])
    frames = []
    sources = []
    for path in sorted(glob.glob(os.path.join(SWEEPS, "*_xs_vec.csv"))):
        frame = pd.read_csv(path)
        if "measure" not in frame.columns or "names" not in frame.columns:
            continue
        kept = frame[frame["measure"].isin(MEASURES) & (frame["names"] == names)]
        if len(kept):
            frames.append(kept)
            sources.append(os.path.basename(path))
    if not frames:
        return names, digest, sources, pd.DataFrame()
    rows = pd.concat(frames, ignore_index=True)
    rows = rows.drop_duplicates("id", keep="last")
    return names, digest, sources, rows


def score():
    names, digest, sources, frame = current_rows()
    cells = frame.to_dict("records") if len(frame) else []
    present = {row["measure"] for row in cells}
    missing = [name for name in MEASURES if name not in present]
    kept = []
    for row in cells:
        mark_usable(row)
        if row["usable"]:
            kept.append(row["id"])
    by_measure = {}
    for name in MEASURES:
        rows = [row for row in cells if row["measure"] == name]
        finite_t = [abs(float(row["t_newey_west"])) for row in rows
                    if row["t_newey_west"] == row["t_newey_west"]]
        by_measure[name] = {
            "cells": len(rows),
            "usable": sum(1 for row in rows if row["usable"]),
            "best_abs_t": None if not finite_t else max(finite_t),
        }
    verdict = "insufficient"
    reason = "no positioning cell has 40 independent observations"
    if any(row["usable"] for row in cells):
        verdict = "recorded"
        reason = ("the cells with 40 independent observations are recorded; "
                  "admission waits on validation and test, which this script does not read")
    return {
        "item": "L6",
        "panel": "data/panel_xs_laevitas",
        "names": names,
        "panel_digest": digest,
        "sources": sources,
        "measures": list(MEASURES),
        "missing_measures": missing,
        "cells": len(cells),
        "usable": len(kept),
        "kept_ids": kept[:20],
        "by_measure": by_measure,
        "verdict": verdict,
        "reason": reason,
        "train_end": sweep_xs.TRAIN_END,
        "min_independent": MIN_INDEPENDENT,
    }


def main():
    payload = score()
    path = write_result("l6_positioning", payload, inputs=[
        "data/panel_xs_laevitas", "results/sweeps"])
    print(path)
    print(payload["verdict"], payload["cells"], payload["usable"], payload["names"])


if __name__ == "__main__":
    main()
