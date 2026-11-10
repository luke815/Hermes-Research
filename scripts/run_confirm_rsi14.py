"""Run the one confirmation attempt for the pre-registered rsi_14 cell."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from regime_tester.confirm import confirm_cell

CELL = "rsi_14|pct_252|above|90|ret_1|eth|none|daily"
ROOT = Path(__file__).resolve().parents[1]

record = confirm_cell(CELL, family_n=6498, train_sign=1, family_combinations=126)
out = ROOT / "results" / "2026-11-10_confirm_rsi_14.json"
payload = {
    "cell_id": CELL,
    "family": "momentum",
    "family_n": record["family_n"],
    "family_combinations": record["family_combinations"],
    "deflated_bar": record["deflated_bar"],
    "train_sign": record["train_sign"],
    "panel_end": record["panel_end"],
    "library_version": record["library_version"],
    "validation": record["validation"],
    "test": record["test"],
    "verdict": record["verdict"],
    "reason": record["reason"],
    "attempted_at": record["attempted_at"],
}
out.write_text(json.dumps(payload, indent=2, default=str))
print(json.dumps(payload, indent=2, default=str))
