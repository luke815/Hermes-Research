"""Neighbour check for the sma_200 cell. Reads the record only. Scores nothing."""

import json
from pathlib import Path

from scripts.pick_next_cell import is_neighbour, parse

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "results" / "sweeps" / "confirmations.json"
OUT = Path("/opt/data/cache/scratch/sma200_neighbour.json")

CELL = "sma_200|chg_7|above|90|ret_3|btc|none|daily"


def main():
    record = json.loads(RECORD.read_text())
    cell = parse(CELL)
    same = [row for row in record if row["cell_id"].startswith("sma_200|")]
    hits = []
    for row in record:
        if row["verdict"] != "rejected":
            continue
        other = parse(row["cell_id"])
        if is_neighbour(cell, other):
            hits.append(row["cell_id"])
    payload = {
        "cell_id": CELL,
        "recorded_sma_200": [
            {"cell_id": row["cell_id"], "verdict": row["verdict"]} for row in same
        ],
        "neighbour_hits": hits,
        "record_rows": len(record),
    }
    OUT.write_text(json.dumps(payload, indent=2))
    print(json.dumps({"same": len(same), "hits": len(hits), "rows": len(record)}))


if __name__ == "__main__":
    main()
