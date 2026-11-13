"""Market-level derivatives and options measures, read from the raw store.

The store keeps each series in several window files, and the windows overlap.
A day is the last row that names it, never an average of the duplicates, and a
row with no numeric value for the measure is a gap rather than a zero. Sub-daily
rows collapse to the UTC date.

A series the store does not carry is absent, not invented. The tenor basis curve
is one of those: the archive holds seven days of it, which is below every
minimum history in the library, so no measure is built from it. SOL is not in
the store at all. The put-call ratio needs an endpoint that returns a server
error, and no butterfly series is served, so both stay out.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

# Tenor labels the options files use. Venue names are excluded so a cross-venue
# basis file, whose columns are exchange names, is not read as a curve.
TENORS = ("1", "7", "14", "30", "60", "90", "180", "270", "365")

# name -> (family, inputs, minimum history, kind)
DERIVATIVES_META = {
    "dvol_level": ("options", ["dvol"], 1, "level"),
    "dvol_chg_7": ("options", ["dvol"], 8, "oscillator"),
    "dvol_pct_252": ("options", ["dvol"], 30, "oscillator"),
    "dvol_minus_rv30": ("options", ["dvol", "realized_vol"], 30, "level"),
    "atm_iv_7": ("options", ["atm_iv"], 1, "level"),
    "atm_iv_30": ("options", ["atm_iv"], 1, "level"),
    "atm_iv_90": ("options", ["atm_iv"], 1, "level"),
    "atm_term_slope": ("options", ["atm_iv"], 1, "level"),
    "atm_inversion": ("options", ["atm_iv"], 1, "flag"),
    "skew_25d_7": ("options", ["skew"], 1, "level"),
    "skew_25d_30": ("options", ["skew"], 1, "level"),
    "skew_25d_90": ("options", ["skew"], 1, "level"),
    "skew_chg_5": ("options", ["skew"], 6, "oscillator"),
    "skew_term_slope": ("options", ["skew"], 1, "level"),
    "risk_reversal_30": ("options", ["risk_reversal"], 1, "level"),
    "basis_venue": ("derivatives", ["basis"], 1, "level"),
    "basis_pct_252": ("derivatives", ["basis"], 30, "oscillator"),
    "perp_premium": ("derivatives", ["basis"], 1, "level"),
    "funding_oiw": ("derivatives", ["funding"], 1, "level"),
    "funding_oiw_avg_7": ("derivatives", ["funding"], 7, "level"),
    "funding_persist_high_oiw": ("derivatives", ["funding"], 30, "count"),
    "funding_persist_low_oiw": ("derivatives", ["funding"], 30, "count"),
    "funding_dispersion_oiw": ("derivatives", ["funding"], 1, "level"),
    "rv_7": ("derivatives", ["close"], 7, "level"),
    "rv_30": ("derivatives", ["close"], 30, "level"),
    "rv_ratio_7_30": ("derivatives", ["close"], 30, "level"),
    "vol_of_vol_30": ("derivatives", ["close"], 60, "level"),
}


def _rows(pattern):
    rows = []
    for path in sorted(RAW.glob(pattern)):
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, list):
            rows.extend(r for r in payload if isinstance(r, dict))
    return rows


def _day(stamp):
    stamp = int(stamp)
    if stamp > 10_000_000_000:
        stamp //= 1000
    return datetime.fromtimestamp(stamp, timezone.utc).date().isoformat()


def daily(pattern, value_fn):
    """One value per UTC day, the last row that has one.

    A row whose value is missing is skipped, so a later empty row cannot blank
    out an earlier real one, and a day with no value is absent.
    """
    out = {}
    for row in _rows(pattern):
        if "date" not in row:
            continue
        value = value_fn(row)
        if value is None or (isinstance(value, float) and np.isnan(value)):
            continue
        out[_day(row["date"])] = float(value)
    if not out:
        return None
    series = pd.Series(out, dtype=float)
    series.index = pd.to_datetime(series.index, utc=True)
    return series.sort_index()


def _num(value):
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def tenor(row, label):
    return _num(row.get(label))


def tenor_mean(row):
    vals = [v for k in TENORS if (v := _num(row.get(k))) is not None]
    return sum(vals) / len(vals) if vals else None


def venue_mean(row):
    """Mean across the venues that reported that day. A missing venue is left out."""
    vals = [_num(v) for k, v in row.items() if k != "date" and not str(k).isdigit()]
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def _percentile(series, window=252, min_periods=30):
    """Trailing percentile rank. Bar t uses only bars before t."""
    def rank_last(window_values):
        past = window_values[:-1]
        past = past[~np.isnan(past)]
        if len(past) < min_periods or np.isnan(window_values[-1]):
            return np.nan
        return float(np.sum(past <= window_values[-1]) / len(past) * 100)

    return series.rolling(window + 1, min_periods=min_periods + 1).apply(rank_last, raw=True)


def _persistence(series, pct=0.8, window=252, min_periods=30):
    """Bars in a row beyond the trailing percentile, high and low separately."""
    hi = series.rolling(window, min_periods=min_periods).quantile(pct)
    lo = series.rolling(window, min_periods=min_periods).quantile(1 - pct)
    above = (series > hi).to_numpy()
    below = (series < lo).to_numpy()
    high = np.zeros(len(series))
    low = np.zeros(len(series))
    for i in range(len(series)):
        high[i] = high[i - 1] + 1 if above[i] else 0
        low[i] = low[i - 1] + 1 if below[i] else 0
    index = series.index
    return pd.Series(high, index=index), pd.Series(low, index=index)


def _asset(asset):
    """Every market-level measure for one asset, from the raw store.

    A measure whose series is missing, or shorter than its minimum history, is
    absent. Nothing is filled forward and nothing is borrowed from the other
    asset.
    """
    out = {}
    dvol = daily(f"dvol_{asset}*.json", lambda r: _num(r.get("dvol")))
    rv7 = daily(f"rv_{asset}*.json", lambda r: tenor(r, "7"))
    rv30 = daily(f"rv_{asset}*.json", lambda r: tenor(r, "30"))
    atm7 = daily(f"atm*{asset}*.json", lambda r: tenor(r, "7"))
    atm30 = daily(f"atm*{asset}*.json", lambda r: tenor(r, "30"))
    atm90 = daily(f"atm*{asset}*.json", lambda r: tenor(r, "90"))
    skew7 = daily(f"skew_{asset}*.json", lambda r: tenor(r, "7"))
    skew30 = daily(f"skew_{asset}*.json", lambda r: tenor(r, "30"))
    skew90 = daily(f"skew_{asset}*.json", lambda r: tenor(r, "90"))
    rr30 = daily(f"rr_{asset}*.json", lambda r: tenor(r, "30"))
    basis = daily(f"basis_{asset}*.json", venue_mean)
    premium = daily(f"oiw_funding_{asset}*.json", lambda r: _num(r.get("apr")))
    funding = daily(f"oiw_funding_{asset}*.json", lambda r: _num(r.get("funding")))
    funding_c = daily(f"oiw_funding_{asset}*.json", lambda r: _num(r.get("funding_c")))
    funding_u = daily(f"oiw_funding_{asset}*.json", lambda r: _num(r.get("funding_u")))

    def keep(name, series):
        if series is not None and series.notna().sum() >= DERIVATIVES_META[name][2]:
            out[name] = series

    if dvol is not None:
        keep("dvol_level", dvol)
        keep("dvol_chg_7", dvol.diff(7))
        keep("dvol_pct_252", _percentile(dvol))
        if rv30 is not None:
            keep("dvol_minus_rv30", (dvol - rv30).dropna())
    keep("atm_iv_7", atm7)
    keep("atm_iv_30", atm30)
    keep("atm_iv_90", atm90)
    if atm7 is not None and atm90 is not None:
        slope = (atm90 - atm7).dropna()
        keep("atm_term_slope", slope)
        keep("atm_inversion", (slope < 0).astype(float))
    keep("skew_25d_7", skew7)
    keep("skew_25d_30", skew30)
    keep("skew_25d_90", skew90)
    if skew30 is not None:
        keep("skew_chg_5", skew30.diff(5))
    if skew7 is not None and skew90 is not None:
        keep("skew_term_slope", (skew90 - skew7).dropna())
    keep("risk_reversal_30", rr30)
    if basis is not None:
        keep("basis_venue", basis)
        keep("basis_pct_252", _percentile(basis))
    keep("perp_premium", premium)
    if funding is not None:
        keep("funding_oiw", funding)
        keep("funding_oiw_avg_7", funding.rolling(7).mean())
        high, low = _persistence(funding)
        keep("funding_persist_high_oiw", high)
        keep("funding_persist_low_oiw", low)
    if funding_c is not None and funding_u is not None:
        keep("funding_dispersion_oiw", (funding_c - funding_u).abs().dropna())
    keep("rv_7", rv7)
    keep("rv_30", rv30)
    if rv7 is not None and rv30 is not None:
        keep("rv_ratio_7_30", (rv7 / rv30.replace(0, np.nan)).dropna())
        keep("vol_of_vol_30", rv30.rolling(30).std())
    return out


def market_measures():
    """Both assets, columns suffixed _btc and _eth. Only what the store holds."""
    frames = []
    for asset in ("btc", "eth"):
        built = _asset(asset)
        if built:
            frames.append(pd.DataFrame(built).add_suffix(f"_{asset}"))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, axis=1).sort_index()
