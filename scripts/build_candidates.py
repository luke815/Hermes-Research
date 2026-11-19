"""The candidates key: top five cross-sectional cells per family, plus today's names.

Reads the vectorized sweep files already on disk, results/sweeps/*_xs_vec.csv,
which the sweep daemon writes. It does not score and it does not pull. A cell
joins the key only when its train independent count is at least 30, it is not
below the minimum, not degenerate and not a duplicate, and it ranks in the top
five of its family by the absolute train t-stat. The side is fade when the
train spread is negative and follow when it is positive.

Today's flagged names are the liquid coins, one row per coin, whose reading on
the last closed day sits on the cell's signalled side. The liquidity floor and
the readings are the ones build_extremes already uses, so the page and the
extremes lists share one universe. A cell whose measure is not one of those
readings is written with an empty names list rather than an invented one.

signals/shadow.csv is started here if it does not exist, one row per cell, and
is never overwritten: the daily shadow update appends to it. Writes only
dashboard/keys/candidates.json. The assembler merges and pushes.
"""

import json
import os
import sys
from glob import glob

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.indicators import META  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWEEPS = os.path.join(ROOT, "results", "sweeps")
PANEL = os.path.join(ROOT, "data", "panel_xs_laevitas")
OUT = os.path.join(ROOT, "dashboard", "keys", "candidates.json")
SHADOW = os.path.join(ROOT, "signals", "shadow.csv")
MIN_N = 30
PER_FAMILY = 5
# A reading build_extremes computes, and which side of it a cell can flag.
READABLE = {
    "funding_rate": "funding_pct",
    "funding": "funding_pct",
    "volume": "volume_ratio",
    "volume_usd": "volume_ratio",
    "oi": "oi_change_7d",
    "oi_usd": "oi_change_7d",
    "close": "stretch",
}
HIGH = 0.80
LOW = 0.20


def load_scored(sweeps=SWEEPS):
    """Every vectorized row, newest file first so a rescored cell keeps its latest row."""
    frames = []
    for path in sorted(glob(os.path.join(sweeps, "*_xs_vec.csv")), reverse=True):
        frame = pd.read_csv(path)
        frame["_file"] = os.path.basename(path)
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    stacked = pd.concat(frames, ignore_index=True)
    return stacked.drop_duplicates("id", keep="first")


def eligible(scored):
    """Cells a candidate may be drawn from: enough train observations, not degenerate."""
    if scored.empty:
        return scored
    keep = (~scored["below_minimum"].astype(bool)
            & ~scored["degenerate"].astype(bool)
            & ~scored["duplicate"].astype(bool)
            & (scored["n_independent"] >= MIN_N))
    return scored[keep].copy()


def top_per_family(scored, meta=META):
    """The top cells of each family, ranked by absolute train t-stat."""
    rows = eligible(scored)
    if rows.empty:
        return []
    rows["family"] = rows["measure"].map(lambda name: meta.get(name, ("unknown",))[0])
    chosen = []
    for family, group in rows.groupby("family"):
        order = group["t_newey_west"].abs().sort_values(ascending=False)
        for _, row in group.reindex(order.index).head(PER_FAMILY).iterrows():
            chosen.append(_cell(row, family))
    return chosen


def _cell(row, family):
    spread = float(row["spread_independent"])
    return {
        "cell_id": row["id"],
        "rule": (f"{row['measure']} {row['transform']} {row['direction']} "
                 f"{int(row['threshold'])}"),
        "family": family,
        "side": "fade" if spread < 0 else "follow",
        "horizon": str(row["target"]).split("_")[-1] + "d",
        "universe": "cross-section",
        "train_net": round(spread, 6),
        "train_t": round(float(row["t_newey_west"]), 4),
        "train_n": int(row["n_independent"]),
        "status": "unconfirmed",
        "measure": row["measure"],
        "transform": row["transform"],
        "direction": row["direction"],
        "threshold": int(row["threshold"]),
    }


def _signalled(reading, direction):
    """Whether a coin's reading sits on the cell's signalled side.

    A percentile reading is high at or above 0.80 and low at or below 0.20.
    A change or a stretch is high when positive and low when negative. A
    missing reading is never signalled.
    """
    if reading is None or pd.isna(reading):
        return False
    if direction == "above":
        return reading >= HIGH if 0 <= reading <= 1 else reading > 0
    return reading <= LOW if 0 <= reading <= 1 else reading < 0


def flagged_names(cells, panel=PANEL):
    """Liquid coins in each cell's signalled state on the last closed day."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import build_extremes
    payload = build_extremes.build(panel)
    rows = []
    for path in sorted(glob(os.path.join(panel, "*.csv"))):
        frame = pd.read_csv(path)
        if "date" not in frame.columns or frame.empty:
            continue
        frame["date"] = frame["date"].astype(str).str.slice(0, 10)
        read = build_extremes.readings(frame, payload["as_of"])
        if read is None:
            continue
        name = os.path.basename(path)[:-4]
        exchange, symbol = name.split("_", 1)
        rows.append({"coin": build_extremes.base_of(symbol), "venue": exchange,
                     "readings": read})
    liquid = build_extremes.liquid(rows)
    for cell in cells:
        inputs = META.get(cell["measure"], (None, []))[1]
        key = next((READABLE[name] for name in inputs if name in READABLE), None)
        names = []
        if key is not None:
            for row in liquid:
                value = row["readings"].get(key)
                if _signalled(value, cell["direction"]):
                    names.append({"symbol": row["coin"],
                                  "value": None if value is None else round(float(value), 4)})
        cell["names"] = names[:10]
        cell.pop("measure", None)
        cell.pop("transform", None)
        cell.pop("direction", None)
        cell.pop("threshold", None)
    return payload["as_of"], cells


def start_shadow(cells, day, path=SHADOW):
    """Create the shadow file if it is absent. Never overwrite an existing one."""
    if os.path.exists(path):
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = ["cell_id,since,n_fires,hit_rate,net_return,vs_backtest"]
    for cell in cells:
        lines.append(f"{cell['cell_id']},{day},0,,,")
    with open(path, "w") as handle:
        handle.write("\n".join(lines) + "\n")
    return True


def build(sweeps=SWEEPS, panel=PANEL):
    """The candidates payload and whether the shadow file was created."""
    cells = top_per_family(load_scored(sweeps))
    as_of, cells = flagged_names(cells, panel)
    created = start_shadow(cells, as_of)
    for cell in cells:
        cell["shadow"] = {"since": as_of, "n_fires": 0, "hit_rate": None,
                          "net_return": 0.0, "vs_backtest": ""}
    return {"as_of": as_of, "cells": cells, "families": sorted({c["family"] for c in cells}),
            "shadow_created": created}


def main():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from dashboard_io import write_key
    payload = build()
    write_key(OUT, {k: v for k, v in payload.items() if k != "shadow_created"})
    print(json.dumps({"as_of": payload["as_of"], "cells": len(payload["cells"]),
                      "families": payload["families"],
                      "shadow_created": payload["shadow_created"]}))


if __name__ == "__main__":
    main()
