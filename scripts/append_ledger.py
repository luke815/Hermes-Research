"""Append today's ledger row from reports/heat_data.json. Idempotent on date."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path("/opt/data/workspace/regime-tester")
heat = json.loads((ROOT / "reports" / "heat_data.json").read_text())

date = heat["dates"][-1]
forecast = heat["predicted"][-1]
price = heat["price"][-1]
score = heat["heat"][-1]
ten = pd.Timestamp(date, tz="UTC") - pd.Timedelta(days=10)
prior_date = ten.date().isoformat()
prior_forecast = None
if prior_date in heat["dates"]:
    prior_forecast = heat["predicted"][heat["dates"].index(prior_date)]
# realized_10d is the return over the NEXT ten days, so today's row cannot have
# one yet. scripts/fix_ledger_forward.py fills a row once the horizon elapses.
realized = None
direction = ""

path = ROOT / "research" / "ledger.csv"
header = "date,heat,forecast_10d,btc_price,prior_forecast_date,prior_forecast,realized_10d,direction_right"
if not path.exists():
    path.write_text(header + "\n")
lines = path.read_text().splitlines()
row = ",".join([
    date,
    f"{score:.4f}",
    "" if forecast is None else f"{forecast:.5f}",
    f"{price:.1f}",
    prior_date,
    "" if prior_forecast is None else f"{prior_forecast:.5f}",
    "" if realized is None else f"{realized:.5f}",
    direction,
])
kept = [line for line in lines if not line.startswith(date + ",")]
kept.append(row)
path.write_text("\n".join(kept) + "\n")
print("appended", row)
print("rows", len(kept) - 1)
