"""Score the pre-registered Donchian-width cell. Chooses nothing."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from regime_tester.confirm import confirm_cell

ROOT = Path(__file__).resolve().parents[1]
CELL = "donchian_width|raw|below|20|ret_1|btc|none|daily"
FAMILY = "volatility"
FAMILY_N = 4590
FAMILY_COMBINATIONS = 90
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

frame = pd.read_csv(ROOT / "results" / "sweeps" / "2026-11-05.csv")
row = frame.loc[frame["id"] == CELL].iloc[0]
train_sign = 1 if float(row["t_newey_west"]) > 0 else -1

record = confirm_cell(CELL, FAMILY_N, train_sign, family_combinations=FAMILY_COMBINATIONS)
out = {
    "date": TODAY,
    "cell_id": CELL,
    "family": FAMILY,
    "family_n": FAMILY_N,
    "family_combinations": FAMILY_COMBINATIONS,
    "rule": "Donchian channel width, raw level below its trailing 20th percentile",
    "train_score": round(float(row["t_newey_west"]), 4),
    "train_spread_pct": round(float(row["spread_independent"]) * 100, 4),
    "train_n": int(row["n_independent"]),
    "train_sign": train_sign,
    "deflated_bar": record["deflated_bar"],
    "panel_end": record["panel_end"],
    "library_version": record["library_version"],
    "validation": record["validation"],
    "test": record["test"],
    "verdict": record["verdict"],
    "reason": record["reason"],
    "attempted_at": record["attempted_at"],
}
path = ROOT / "results" / f"{TODAY}_confirm_donchian_raw.json"
path.write_text(json.dumps(out, indent=2, default=str) + "\n")
print(path)


def side(block, key):
    if block is None:
        return None
    return block[key]


print(json.dumps({
    "verdict": record["verdict"],
    "reason": record["reason"],
    "bar": record["deflated_bar"],
    "train_sign": train_sign,
    "train_score": out["train_score"],
    "train_spread_pct": out["train_spread_pct"],
    "train_n": out["train_n"],
    "validation_spread": side(record["validation"], "spread_independent"),
    "validation_t": side(record["validation"], "t_newey_west"),
    "validation_n": side(record["validation"], "n_independent"),
    "validation_years": side(record["validation"], "year_signs"),
    "test_spread": side(record["test"], "spread_independent"),
    "test_t": side(record["test"], "t_newey_west"),
    "test_n": side(record["test"], "n_independent"),
    "test_years": side(record["test"], "year_signs"),
    "panel_end": record["panel_end"],
}, indent=2))
