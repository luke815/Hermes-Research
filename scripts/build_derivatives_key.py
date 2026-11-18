"""Write the derivatives key from the raw store. No invented values.

Reads the market-level series already on disk through
regime_tester.derivatives, so a day the store does not hold is absent
rather than filled. Writes only dashboard/keys/derivatives.json. The
assembler merges it into data.json and pushes; this script does neither.
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.derivatives import DERIVATIVES_META, _asset

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "dashboard", "keys", "derivatives.json")
SPARK = 30
PCT_WINDOW = 365
PCT_MIN = 30

UNITS = {
    "dvol_level": "", "dvol_chg_7": "", "dvol_pct_252": "pct", "dvol_minus_rv30": "pts",
    "atm_iv_7": "%", "atm_iv_30": "%", "atm_iv_90": "%", "atm_term_slope": "pts",
    "atm_inversion": "", "skew_25d_7": "", "skew_25d_30": "", "skew_25d_90": "",
    "skew_chg_5": "", "skew_term_slope": "", "risk_reversal_30": "",
    "basis_venue": "%", "basis_pct_252": "pct",
    "funding_oiw": "", "funding_oiw_avg_7": "", "funding_persist_high_oiw": "days",
    "funding_persist_low_oiw": "days", "funding_dispersion_oiw": "",
    "rv_7": "%", "rv_30": "%", "rv_ratio_7_30": "", "vol_of_vol_30": "",
}
DECIMALS = {
    "funding_oiw": 6, "funding_oiw_avg_7": 6, "funding_dispersion_oiw": 6,
    "basis_venue": 4,
}


def _pct_1y(series):
    """Share of the trailing year at or below the last value. Past bars only."""
    past = series.dropna().iloc[-(PCT_WINDOW + 1):-1]
    if len(past) < PCT_MIN:
        return None
    return round(float((past <= series.dropna().iloc[-1]).mean()), 4)


def _note(name, pct):
    if pct is None:
        return "no trailing year yet"
    band = "low" if pct < 0.2 else "high" if pct > 0.8 else "mid-range"
    return f"{name.replace('_', ' ')} {band} against its trailing year ({round(pct * 100):.0f}th percentile)"


def _round(name, value):
    places = DECIMALS.get(name, 2)
    return round(float(value), places)


def build():
    today = datetime.now(timezone.utc).date().isoformat()
    assets = {}
    ends = []
    for asset in ("btc", "eth"):
        rows = []
        for name, series in _asset(asset).items():
            clean = series.dropna()
            if clean.empty:
                continue
            ends.append(clean.index[-1].date().isoformat())
            last = clean.iloc[-1]
            prev = clean.iloc[-2] if len(clean) > 1 else None
            week = clean.iloc[-8] if len(clean) > 7 else None
            spark = [_round(name, v) for v in clean.iloc[-SPARK:]]
            rows.append({
                "name": name,
                "as_of": clean.index[-1].date().isoformat(),
                "value": _round(name, last),
                "unit": UNITS.get(name, ""),
                "chg_1d": None if prev is None else _round(name, last - prev),
                "chg_7d": None if week is None else _round(name, last - week),
                "pct_1y": _pct_1y(series),
                "spark": spark,
                "note": _note(name, _pct_1y(series)),
                "decimals": DECIMALS.get(name, 2),
            })
        assets[asset.upper()] = rows
    if not ends:
        raise SystemExit("no market-level series on disk")
    as_of = max(ends)
    age = (datetime.fromisoformat(today) - datetime.fromisoformat(as_of)).days
    if age > 2:
        raise SystemExit(f"store ends {as_of}, {age}d behind {today}")
    missing = [a for a in ("BTC", "ETH") if not assets[a]]
    if missing:
        raise SystemExit(f"no series for {missing}")
    unknown = [r["name"] for rows in assets.values() for r in rows if r["name"] not in DERIVATIVES_META]
    if unknown:
        raise SystemExit(f"series outside the library: {unknown}")
    return {"as_of": as_of, "built": today, "assets": assets}


def main():
    payload = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"
    json.dump(payload, open(tmp, "w"))
    os.replace(tmp, OUT)
    counts = {asset: len(rows) for asset, rows in payload["assets"].items()}
    print(f"wrote {OUT} as_of={payload['as_of']} built={payload['built']} series={counts}")


if __name__ == "__main__":
    main()
