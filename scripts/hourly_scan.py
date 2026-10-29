"""Hourly health scan. Reads data/panel.csv. Never writes it.

Writes results/<today>_hourly.json only.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path("/opt/data/workspace/regime-tester")
sys.path.insert(0, str(ROOT))

from regime_tester.heat import COMPONENTS, heat_score
from regime_tester.ta import atr_regime, moving_average_structure

BAND = 0.4
HORIZON = 10


def zone(value: float) -> str:
    if value >= BAND:
        return "hot"
    if value <= -BAND:
        return "cold"
    return "mid"


def main() -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    written = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    panel = pd.read_csv(ROOT / "data" / "panel.csv", index_col=0, parse_dates=True)
    panel.index = pd.to_datetime(panel.index, utc=True)
    scored = heat_score(panel)
    heat = scored["heat"].dropna()
    last_ts = heat.index[-1]
    prev_ts = heat.index[-2]
    heat_now = float(heat.iloc[-1])
    heat_prev_bar = float(heat.iloc[-2])

    legs = {}
    for name in COMPONENTS:
        series = scored[f"leg_{name}"].dropna()
        legs[name] = {
            "now": float(series.iloc[-1]),
            "prev": float(series.iloc[-2]),
        }

    btc = panel["btc_price"].dropna()
    eth = panel["eth_price"].dropna()
    alt_cols = [c for c in panel.columns if c.endswith("_price") and c not in ("btc_price", "eth_price")]
    alt = panel[alt_cols].mean(axis=1).dropna() if alt_cols else pd.Series(dtype=float)

    def last_ta(price: pd.Series) -> dict:
        ma = moving_average_structure(price)
        atr = atr_regime(price)
        return {
            "date": price.index[-1].date().isoformat(),
            "slope_ma20": None if pd.isna(ma["slope_ma20"].iloc[-1]) else float(ma["slope_ma20"].iloc[-1]),
            "atr_regime": None if pd.isna(atr.iloc[-1]) else float(atr.iloc[-1]),
        }

    ta = {
        "btc": last_ta(btc),
        "eth": last_ta(eth),
        "alt": last_ta(alt) if len(alt) else None,
        "alt_price_cols": alt_cols,
    }

    results_dir = ROOT / "results"
    prior_path = results_dir / f"{today}_hourly.json"
    prior = json.loads(prior_path.read_text()) if prior_path.exists() else {}

    # A standalone signal "agrees" only as a long when heat is in the OOS zone
    # (above +0.4) and slope_ma20 is positive. Cold is not an actionable zone.
    agrees = []
    if heat_now >= BAND:
        for asset, reading in (("btc", ta["btc"]), ("eth", ta["eth"]), ("alt", ta["alt"])):
            if not reading:
                continue
            slope = reading["slope_ma20"]
            if slope is not None and slope > 0:
                agrees.append({
                    "asset": asset,
                    "direction": "long",
                    "horizon_days": HORIZON,
                    "slope_ma20": slope,
                    "atr_regime": reading["atr_regime"],
                    "date": reading["date"],
                })

    payload = {
        "job": "hourly-health",
        "written_utc": written,
        "today": today,
        "panel_end": last_ts.date().isoformat(),
        "panel_prev": prev_ts.date().isoformat(),
        "panel_rows": int(len(panel)),
        "heat": heat_now,
        "heat_prev_bar": heat_prev_bar,
        "zone": zone(heat_now),
        "prev_bar_zone": zone(heat_prev_bar),
        "crossed_plus_0_4_vs_prev_bar": heat_prev_bar < BAND and heat_now >= BAND,
        "crossed_minus_0_4_vs_prev_bar": heat_prev_bar > -BAND and heat_now <= -BAND,
        "legs": legs,
        "ta": ta,
        "prior_run_written": prior.get("written_utc"),
        "prior_run_heat": prior.get("heat"),
        "prior_run_zone": prior.get("zone"),
        "prior_run_qualifying": prior.get("qualifying_setups"),
        "heat_delta_vs_prior_run": None if prior.get("heat") is None else heat_now - float(prior["heat"]),
        "crossed_plus_0_4_vs_prior_run": (
            None if prior.get("heat") is None else (float(prior["heat"]) < BAND and heat_now >= BAND)
        ),
        "crossed_minus_0_4_vs_prior_run": (
            None if prior.get("heat") is None else (float(prior["heat"]) > -BAND and heat_now <= -BAND)
        ),
        "oos_zone": heat_now >= BAND,
        "qualifying_setups": len(agrees),
        "qualifying": agrees,
        "setups_file": (ROOT / "signals" / "setups.md").exists(),
    }
    out = results_dir / f"{today}_hourly.json"
    out.write_text(json.dumps(payload, indent=2))
    print(out)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
