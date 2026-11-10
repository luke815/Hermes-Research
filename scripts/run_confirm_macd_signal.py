"""Run the one confirmation attempt for the pre-registered macd_signal cell."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from regime_tester.confirm import confirm_cell

CELL = "macd_signal|raw|below|20|rel_3|eth|none|daily"
ROOT = Path(__file__).resolve().parents[1]

record = confirm_cell(CELL, family_n=16848, train_sign=-1, family_combinations=324)
out = ROOT / "results" / "2026-11-10_confirm_macd_signal.json"
payload = {
    "cell_id": CELL,
    "family": "trend",
    "family_n": record["family_n"],
    "family_combinations": record["family_combinations"],
    "deflated_bar": record["deflated_bar"],
    "train_sign": record["train_sign"],
    "train_score": -3.4383,
    "train_spread_pct": -1.2643,
    "train_n": 102,
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
