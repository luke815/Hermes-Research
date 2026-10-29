"""Hourly health. Reads panel. Writes results/<today>_hourly.json. Never writes panel.csv."""

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
MAX_AGE = 2


def zone(value: float) -> str:
    if value >= BAND:
        return "hot"
    if value <= -BAND:
        return "cold"
    return "mid"


def verify_panel(path: Path, today: datetime) -> dict:
    panel = pd.read_csv(path, index_col=0, parse_dates=True)
    panel.index = pd.to_datetime(panel.index, utc=True)
    panel = panel.sort_index()
    end = panel.index.max()
    age = (today.date() - end.date()).days
    dupes = int(panel.index.duplicated().sum())
    if len(panel.index) > 1:
        gaps = panel.index.to_series().diff().dt.days
        missing_days = int((gaps[gaps > 1] - 1).sum())
    else:
        missing_days = 0
    numeric = panel.select_dtypes(include="number")
    nan_share = {c: float(numeric[c].isna().mean()) for c in numeric.columns}
    trailing_blank = [
        c for c in numeric.columns if numeric[c].iloc[-1] != numeric[c].iloc[-1]
    ]
    fill_forward = []
    jumps = []
    for c in numeric.columns:
        values = numeric[c].dropna()
        if len(values) < 8:
            continue
        same = values == values.shift(1)
        run = 0
        longest = 0
        run_end = None
        for ts, flag in same.fillna(False).items():
            if flag:
                run += 1
                if run > longest:
                    longest = run
                    run_end = ts
            else:
                run = 0
        if longest >= 5 and values.nunique() > 1 and run_end is not None and (values.index[-1] - run_end).days <= 3:
            fill_forward.append(c)
        delta = values.diff().dropna()
        if len(delta) < 30:
            continue
        scale = float(delta.abs().median())
        if scale == 0:
            continue
        last_jump = abs(float(delta.iloc[-1]))
        if last_jump > 20 * scale and last_jump > float(delta.abs().quantile(0.999)):
            jumps.append(c)
    reasons = []
    if age > MAX_AGE:
        reasons.append(f"age {age}d > {MAX_AGE}")
    if dupes:
        reasons.append(f"duplicate dates {dupes}")
    if trailing_blank:
        reasons.append(f"trailing blanks {trailing_blank}")
    if fill_forward:
        reasons.append(f"fill_forward {fill_forward}")
    if jumps:
        reasons.append(f"jumps {jumps}")
    status = "FAIL" if reasons else "PASS"
    summary = (
        f"{status} panel_end={end.date().isoformat()} today={today.date().isoformat()} "
        f"age={age}d rows={len(panel)} trailing_blank_cols={len(trailing_blank)} "
        f"dupes={dupes} missing_days={missing_days}"
    )
    if reasons:
        summary += " reasons=" + ";".join(reasons)
    return {
        "status": status,
        "summary": summary,
        "panel_end": end.date().isoformat(),
        "age": age,
        "rows": int(len(panel)),
        "dupes": dupes,
        "missing_days": missing_days,
        "trailing_blank_cols": trailing_blank,
        "nan_share_max": max(nan_share.values()) if nan_share else None,
        "panel": panel,
    }


def last_ta(price: pd.Series) -> dict:
    ma = moving_average_structure(price)
    atr = atr_regime(price)
    return {
        "date": price.index[-1].date().isoformat(),
        "slope_ma20": None if pd.isna(ma["slope_ma20"].iloc[-1]) else float(ma["slope_ma20"].iloc[-1]),
        "atr_regime": None if pd.isna(atr.iloc[-1]) else float(atr.iloc[-1]),
    }


def main() -> None:
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    written = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    check = verify_panel(ROOT / "data" / "panel.csv", now)
    print(check["summary"])
    if check["status"] != "PASS":
        out = ROOT / "results" / f"{today}_hourly.json"
        payload = {
            "job": "hourly-health",
            "written_utc": written,
            "today": today,
            "verify_panel": check["summary"],
            "status": "FAIL",
        }
        out.write_text(json.dumps(payload, indent=2))
        print(out)
        sys.exit(1)

    panel = check["panel"]
    scored = heat_score(panel)
    heat = scored["heat"].dropna()
    last_ts = heat.index[-1]
    prev_ts = heat.index[-2]
    heat_now = float(heat.iloc[-1])
    heat_prev_bar = float(heat.iloc[-2])

    legs = {}
    for name in COMPONENTS:
        series = scored[f"leg_{name}"].dropna()
        legs[name] = {"now": float(series.iloc[-1]), "prev": float(series.iloc[-2])}

    btc = panel["btc_price"].dropna()
    eth = panel["eth_price"].dropna()
    alt_cols = [c for c in panel.columns if c.endswith("_price") and c not in ("btc_price", "eth_price")]
    alt = panel[alt_cols].mean(axis=1).dropna() if alt_cols else pd.Series(dtype=float)
    ta = {
        "btc": last_ta(btc),
        "eth": last_ta(eth),
        "alt": last_ta(alt) if len(alt) else None,
        "alt_price_cols": alt_cols,
    }

    results_dir = ROOT / "results"
    prior_path = results_dir / f"{today}_hourly.json"
    prior = json.loads(prior_path.read_text()) if prior_path.exists() else {}
    if not prior:
        candidates = sorted(results_dir.glob("*_hourly.json"))
        if candidates:
            prior = json.loads(candidates[-1].read_text())
            prior["_source"] = str(candidates[-1].name)

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
        "age_days": check["age"],
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
        "prior_run_file": prior.get("_source") or (prior_path.name if prior else None),
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
        "verify_panel": check["summary"],
        "verify_note": "scripts/verify_panel.py missing; checks run inside scripts/hourly_health.py",
    }
    out = results_dir / f"{today}_hourly.json"
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(out)
    print(json.dumps({k: payload[k] for k in (
        "heat", "zone", "panel_end", "age_days", "qualifying_setups",
        "crossed_plus_0_4_vs_prior_run", "crossed_minus_0_4_vs_prior_run",
        "heat_delta_vs_prior_run", "prior_run_qualifying",
    )}))


if __name__ == "__main__":
    main()
