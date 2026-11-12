"""Family counts and neighbour check for the chosen cell. Scores nothing."""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from regime_tester.indicators import META
from scripts.pick_next_cell import is_neighbour, parse

ROOT = Path("/opt/data/workspace/regime-tester")
CELL = "td_setup|chg_3|below|10|ret_1|eth|none|daily"

frame = pd.read_csv(ROOT / "results" / "sweeps" / "2026-11-05.csv")
family_of = {name: meta[0] for name, meta in META.items()}
frame["family"] = frame["measure"].map(family_of)
cycle = frame[frame["family"] == "cycle"]
combos = cycle.groupby(["measure", "target", "universe"]).ngroups
row = frame.loc[frame["id"] == CELL].iloc[0]

record = json.loads((ROOT / "results" / "sweeps" / "confirmations.json").read_text())
closed = [parse(item["cell_id"]) for item in record if item["verdict"] == "rejected"]
cell = parse(CELL)
hits = [item["cell_id"] for item in closed if is_neighbour(cell, item)]
td_rows = [
    {"cell_id": item["cell_id"], "verdict": item["verdict"]}
    for item in record
    if item["cell_id"].startswith("td_")
]
board = json.loads((ROOT / "results" / "sweeps" / "leaderboard.json").read_text())
out = {
    "leaderboard_as_of": board["as_of"],
    "leaderboard_source": board["source"],
    "leaderboard_top": board["leaderboard"][0]["cell_id"],
    "cycle_rows": int(len(cycle)),
    "cycle_combinations": int(combos),
    "train_t": round(float(row["t_newey_west"]), 4),
    "train_spread": round(float(row["spread_independent"]) * 100, 4),
    "train_n": int(row["n_independent"]),
    "fragile": str(row["fragile"]),
    "duplicate": str(row["duplicate"]),
    "neighbour_hits": hits,
    "td_recorded": td_rows,
    "already": any(item["cell_id"] == CELL for item in record),
}
Path("/opt/data/cache/scratch/td_setup_check.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
