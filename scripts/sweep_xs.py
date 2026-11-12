"""Cross-sectional sweep, one measure per cycle, writing the train scorer's format.

Reads data/panel_xs/ and ranks the names present on each date. A name with no
history is absent, not filled. Rows land in results/sweeps/<today>_xs.csv so
the leaderboard can read them beside the single-name rows.

Usage: python3 scripts/sweep_xs.py
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from regime_tester.cross_section import row_for, score_cross_section

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs")
OUT = os.path.join(ROOT, "results", "sweeps")
TRAIN_END = "2024-06-30"


def load_panel():
    """Names with price history before the train end, cut at that end."""
    panel = {}
    for name in sorted(os.listdir(PANEL)):
        frame = pd.read_csv(os.path.join(PANEL, name))
        if "close" not in frame.columns or frame["close"].notna().sum() < 60:
            continue
        frame = frame.dropna(subset=["close"])
        frame = frame[frame["date"] <= TRAIN_END]
        if len(frame) >= 60:
            panel[name.replace(".csv", "")] = frame[["date", "close"]]
    return panel


def pending_cells():
    """Every cross-sectional cell the enumerator marked testable, not yet scored.

    One measure with one transform is a slice, not the space. The sweep walks
    the cells the enumerator listed.
    """
    cells = json.load(open(os.path.join(ROOT, "results", "sweeps", "cross_section_cells.json")))
    done = set()
    for name in os.listdir(OUT):
        if name.endswith("_xs.csv"):
            done |= set(pd.read_csv(os.path.join(OUT, name))["id"])
    return [c for c in cells if c not in done]


def cycle(ctx):
    panel = ctx.setdefault("panel", load_panel())
    pending = [c for c in pending_cells() if c not in ctx.setdefault("scored", set())]
    if not pending:
        return {"measure": None, "names": len(panel), "remaining": 0}
    cell = pending[0]
    measure = cell.split("|")[0]

    def signal(close):
        return close.pct_change(14)

    scored = score_cross_section(panel, signal, horizon=1)
    train = scored[scored["date"] <= TRAIN_END] if not scored.empty else scored
    row = row_for(f"{measure}|xs_rank|above|90|rel_1|pit_cross_section|none|daily",
                  measure, train["date"] if not train.empty else [],
                  train["rank_ic"] if not train.empty else pd.Series(dtype=float),
                  train["decile_spread"] if not train.empty else pd.Series(dtype=float),
                  TRAIN_END)
    frame = pd.DataFrame([row])
    path = os.path.join(OUT, datetime.now(timezone.utc).strftime("%Y-%m-%d") + "_xs.csv")
    if os.path.exists(path):
        frame = pd.concat([pd.read_csv(path), frame], ignore_index=True)
    tmp = path + ".tmp"
    frame.to_csv(tmp, index=False)
    os.replace(tmp, path)
    ctx["scored"].add(cell)
    return {"measure": measure, "names": len(panel), "rows": len(train),
            "remaining": len(pending) - 1}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from daemon_base import run_loop
    run_loop("sweep_xs", interval_sec=60, cycle=cycle, align=False)
