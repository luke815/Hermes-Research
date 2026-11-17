"""Write the heat_stats key from the panel. No invented values.

Forward BTC returns by heat zone, horizons 10d and 30d, periods train,
validation and test. Zones are fixed at ±0.40, the same cut the hourly
scan uses. Windows are non-overlapping: every h-th bar, stride taken once
from the first bar that has both a score and a closed window, so the same
bars are used in every period. n is that independent count.

Writes only dashboard/keys/heat_stats.json. The assembler merges it into
data.json and pushes; this script does neither.
"""

import json
import os
import sys
from datetime import datetime, timezone

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from regime_tester.heat import heat_score
from regime_tester.periods import PERIODS, assign_period

PANEL = os.path.join(ROOT, "data", "panel.csv")
OUT = os.path.join(ROOT, "dashboard", "keys", "heat_stats.json")
BAND = 0.40
HORIZONS = (10, 30)
ZONES = ("hot", "mid", "cold")


def zone_of(value):
    if value >= BAND:
        return "hot"
    if value <= -BAND:
        return "cold"
    return "mid"


def row(frame, zone, horizon, period):
    part = frame[(frame["zone"] == zone) & (frame["period"] == period)]
    values = part["fwd"].dropna()
    n = int(len(values))
    if n == 0:
        return {"zone": zone, "horizon": f"{horizon}d", "period": period,
                "mean": None, "hit": None, "n": 0}
    return {
        "zone": zone,
        "horizon": f"{horizon}d",
        "period": period,
        "mean": round(float(values.mean()) * 100, 4),
        "hit": round(float((values > 0).mean()), 4),
        "n": n,
    }


def build():
    today = datetime.now(timezone.utc).date().isoformat()
    panel = pd.read_csv(PANEL, index_col=0, parse_dates=True)
    panel.index = pd.to_datetime(panel.index, utc=True)
    scored = heat_score(panel)
    heat = scored["heat"]
    price = scored["btc_price"]
    period = assign_period(heat.index)

    frames = {}
    for horizon in HORIZONS:
        forward = price.shift(-horizon) / price - 1
        both = pd.concat([
            heat.rename("heat"),
            forward.rename("fwd"),
            period,
        ], axis=1).dropna()
        stride = both.iloc[::horizon]
        stride = stride.copy()
        stride["zone"] = stride["heat"].map(zone_of)
        frames[horizon] = stride

    rows = [
        row(frames[horizon], zone, horizon, name)
        for zone in ZONES
        for horizon in HORIZONS
        for name, _, _ in PERIODS
    ]

    latest = heat.dropna()
    current = zone_of(float(latest.iloc[-1]))
    as_of = pd.Timestamp(latest.index[-1]).date().isoformat()
    age = (datetime.now(timezone.utc).date() - pd.Timestamp(latest.index[-1]).date()).days
    if age > 2:
        raise SystemExit(f"panel ends {as_of}, {age} days behind today")
    payload = {
        "as_of": as_of,
        "built": today,
        "current_zone": current,
        "band": BAND,
        "rows": rows,
        "note": (
            "BTC forward return while heat was hot (above +0.40), mid, or "
            "cold (below -0.40). Mean is percent, hit is the share of those "
            "days that closed up, n is non-overlapping: one bar per horizon "
            "so a 10-day window is counted once. Train through 2024-06-30, "
            "validation through 2025-12-31, test from 2026-01-01. A reading, "
            "not a signal."
        ),
    }
    if len(rows) != len(ZONES) * len(HORIZONS) * len(PERIODS):
        raise SystemExit(f"expected 18 rows, wrote {len(rows)}")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"
    with open(tmp, "w") as handle:
        json.dump(payload, handle, indent=1)
    os.replace(tmp, OUT)
    return payload


if __name__ == "__main__":
    result = build()
    print("as_of", result["as_of"], "zone", result["current_zone"], "rows", len(result["rows"]))
    for item in result["rows"]:
        print(f"{item['zone']:4} {item['horizon']:4} {item['period']:10} mean={item['mean']} hit={item['hit']} n={item['n']}")
