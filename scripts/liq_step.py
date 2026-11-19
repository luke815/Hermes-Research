"""Daily BTC liquidation total around the 2026 jump, to see if it steps or drifts."""

import json
from datetime import datetime, timezone

raw = json.load(open("data/raw/coinalyze_liquidation-history.json"))
for series in raw["data"]:
    if series["symbol"] != "BTCUSDT_PERP.A":
        continue
    for bar in series["history"]:
        day = datetime.fromtimestamp(bar["t"], timezone.utc).strftime("%Y-%m-%d")
        if "2026-01-25" <= day <= "2026-02-10":
            print(day, round((bar["l"] + bar["s"]) / 1e6, 1))
