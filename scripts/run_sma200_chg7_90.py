"""Confirm the pre-registered sma_200 cell. One attempt, recorded as it finishes."""

import json
from pathlib import Path

from regime_tester.confirm import confirm_cell

ROOT = Path(__file__).resolve().parents[1]
PICK = Path("/opt/data/cache/scratch/next_cell.json")
OUT = ROOT / "results" / "2026-11-12_confirm_sma200_chg7_90.json"


def main():
    pick = json.loads(PICK.read_text())
    record = confirm_cell(
        pick["cell_id"],
        family_n=pick["family_n"],
        train_sign=1 if pick["train_score"] > 0 else -1,
        family_combinations=pick["family_combinations"],
    )
    OUT.write_text(json.dumps(record, indent=2, default=str))
    print(json.dumps({
        "verdict": record["verdict"],
        "reason": record["reason"],
        "bar": record["deflated_bar"],
        "val_n": None if record["validation"] is None else record["validation"]["n_independent"],
        "val_t": None if record["validation"] is None else record["validation"]["t_newey_west"],
        "test_n": None if record["test"] is None else record["test"]["n_independent"],
        "panel_end": record["panel_end"],
        "out": str(OUT),
    }))


if __name__ == "__main__":
    main()
