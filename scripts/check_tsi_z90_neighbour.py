"""Neighbour check for the TSI 90-bar cell. Reads the confirmation record only. Scores nothing."""

import json
from pathlib import Path

from scripts.pick_next_cell import is_neighbour, parse

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "results" / "sweeps" / "confirmations.json"
BOARD = ROOT / "results" / "sweeps" / "leaderboard.json"
CELL = "tsi|z_90|below|5|ret_1|eth|none|daily"
OUT = Path("/opt/data/cache/scratch/tsi_z90_neighbour.json")


def main():
    record = json.loads(RECORD.read_text())
    board = json.loads(BOARD.read_text())
    cell = parse(CELL)
    same = [row for row in record if row["cell_id"].split("|")[0] == "tsi"]
    hits = []
    for row in record:
        if row["verdict"] != "rejected":
            continue
        closed = parse(row["cell_id"])
        if is_neighbour(cell, closed):
            hits.append(row["cell_id"])
    payload = {
        "cell_id": CELL,
        "leaderboard_as_of": board["as_of"],
        "leaderboard_source": board["source"],
        "leaderboard_top": board["leaderboard"][0]["cell_id"],
        "recorded_tsi": [row["cell_id"] for row in same],
        "recorded_total": len(record),
        "rejected_total": sum(1 for row in record if row["verdict"] == "rejected"),
        "neighbour_hits": hits,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
