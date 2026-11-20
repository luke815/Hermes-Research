"""Find the name behind the A7(1) 3-day test spread.

The committed scorer reported an 83 percent test spread on the 3-day window
at the 3-day horizon. That number is one name until this script says otherwise.
It reads the panel already on disk, applies the pre-registered rule, and writes
the date and the name that carry the spread. No pull.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from regime_tester.results_io import write_result  # noqa: E402
from scripts.score_a7_reversal import (  # noqa: E402
    PRIMARY_FLOOR, load_matrices, loser_signal, net_return, vol_scale,
)

OUT = Path("/tmp/a7_outlier_progress.txt")


def note(text):
    OUT.write_text(text)
    print(text, flush=True)


def main():
    close, oi, funding = load_matrices()
    signal = loser_signal(close, 3)
    scale = vol_scale(close)
    gross, net = net_return(close, funding, oi, 3)
    btc = close["BTC"]
    excess = gross.sub(btc.shift(-3) / btc - 1, axis=0)
    sig = signal.to_numpy(dtype=float)
    sc = scale.to_numpy(dtype=float)
    gr = excess.to_numpy(dtype=float)
    nt = net.to_numpy(dtype=float)
    oi_v = oi.to_numpy(dtype=float)
    ok = (np.isfinite(sig) & np.isfinite(sc) & np.isfinite(gr) & np.isfinite(nt)
          & np.isfinite(oi_v) & (oi_v >= PRIMARY_FLOOR))
    ranked = pd.DataFrame(np.where(ok, sig, np.nan)).rank(axis=1, pct=True)
    pct = ranked.to_numpy(dtype=float)
    long_m = ok & (pct >= 0.9)
    test = close.index >= pd.Timestamp("2026-01-01", tz="UTC")
    stride = np.zeros(len(close), dtype=bool)
    stride[np.flatnonzero(test)[::3]] = True
    names = list(close.columns)
    rows = []
    for i in np.flatnonzero(stride):
        cols = np.flatnonzero(long_m[i])
        if not len(cols):
            continue
        weights = sc[i, cols]
        contrib = nt[i, cols] * weights / weights.sum()
        top = int(np.nanargmax(np.abs(contrib)))
        rows.append({
            "date": str(close.index[i].date()),
            "names": int(ok[i].sum()),
            "long_n": int(len(cols)),
            "spread_from_top": float(contrib[top] * 100),
            "name": names[cols[top]],
            "net": float(nt[i, cols[top]] * 100),
            "weight": float(weights[top] / weights.sum()),
        })
    rows.sort(key=lambda r: -abs(r["spread_from_top"]))
    note(json.dumps({"worst": rows[:5], "dates": len(rows)}))
    payload = {"candidate": "a7_reversal_outlier", "dates": len(rows), "worst": rows[:10]}
    path = write_result("a7_reversal_outlier", payload, inputs=["data/panel_xs_laevitas"])
    print(path)


if __name__ == "__main__":
    main()
