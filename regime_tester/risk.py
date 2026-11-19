"""R1 inputs and the R2 dial, from series already on disk.

Every input is trailing. A percentile compares today's value with the year
strictly before it, and a missing series is recorded as unavailable rather
than filled. The state machine follows RISK_REGIME.md section 2 with the
hysteresis stated there: a state does not change again inside five days
unless a capitulation or cascade flag is on. The dial is the middle of the
state's band, scaled by volatility and floored at 0.5 and capped at 1.3.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

STATES = (
    "risk_on_trend",
    "risk_on_early",
    "neutral",
    "risk_off_distribution",
    "risk_off_trend_down",
    "defensive_after_capitulation",
)
BANDS = {
    "risk_on_trend": (1.00, 1.30),
    "risk_on_early": (0.70, 1.00),
    "neutral": (0.60, 0.80),
    "risk_off_distribution": (0.30, 0.50),
    "risk_off_trend_down": (0.10, 0.30),
    "defensive_after_capitulation": (0.20, 0.40),
}
HYSTERESIS_DAYS = 5
PCT_WINDOW = 365
PCT_MIN = 30
VOL_TARGET = 0.60
VOL_FLOOR, VOL_CAP = 0.5, 1.3


def _round(value, places):
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return None
    return round(float(value), places)


def percentile(series, window=PCT_WINDOW, minimum=PCT_MIN):
    """Share of the trailing window strictly before each bar at or below it."""
    values = series.to_numpy(dtype=float)
    out = np.full(len(values), np.nan)
    for i in range(len(values)):
        if not np.isfinite(values[i]):
            continue
        past = values[max(0, i - window):i]
        past = past[np.isfinite(past)]
        if len(past) >= minimum:
            out[i] = float((past <= values[i]).mean())
    return pd.Series(out, index=series.index)


def weekly_position(close):
    """Where daily price sits against the 20-week SMA and 21-week EMA.

    Weeks close on Sunday, and the band at bar t uses only weeks already
    closed, so a price printed later in the week cannot move an earlier bar.
    Returns position (above, inside, below), the distance to the band edge
    in percent, and the weeks since the last cross of either edge.
    """
    weekly = close.resample("W-SUN").last().dropna()
    sma = weekly.rolling(20).mean()
    ema = weekly.ewm(span=21, adjust=False).mean()
    band = pd.DataFrame({"lo": np.minimum(sma, ema), "hi": np.maximum(sma, ema)})
    band = band.shift(1).reindex(close.index, method="ffill")
    position = pd.Series(np.nan, index=close.index, dtype="object")
    known = band["hi"].notna() & close.notna()
    position[known & (close > band["hi"])] = "above"
    position[known & (close < band["lo"])] = "below"
    position[known & (close >= band["lo"]) & (close <= band["hi"])] = "inside"
    edge = pd.Series(np.where(close.to_numpy() >= band["hi"].to_numpy(),
                              band["hi"].to_numpy(), band["lo"].to_numpy()), index=close.index)
    distance = (close / edge - 1) * 100
    distance = distance.where(position.notna())
    previous = position.shift(1)
    crossed = position.notna() & previous.notna() & position.ne(previous)
    weeks = pd.Series(np.nan, index=close.index)
    last = None
    for i, (stamp, flag) in enumerate(crossed.items()):
        if flag:
            last = stamp
        if last is not None and pd.notna(position.iloc[i]):
            weeks.iloc[i] = (stamp - last).days / 7
    return position, distance, weeks


def _flag(name, value, pct, flag, effect, available=True):
    return {"name": name, "value": value, "pct": pct, "flag": flag,
            "effect": effect, "available": available}


def unavailable(name):
    return _flag(name, None, None, "unavailable", "none", available=False)


def inputs_on(row):
    """The section-1 inputs for one day, each with a flag and an effect.

    `row` carries the trailing readings already computed. A key that is
    absent or null becomes an unavailable input, so the dial never treats a
    gap as a calm reading.
    """
    out = []

    def has(key):
        return key in row and row[key] is not None and not (isinstance(row[key], float) and np.isnan(row[key]))

    if has("btc_vs_200d"):
        value = row["btc_vs_200d"]
        out.append(_flag("btc_vs_200d", _round(value, 2), None,
                          "above" if value >= 0 else "below",
                          "risk_on" if value >= 0 else "risk_off"))
    else:
        out.append(unavailable("btc_vs_200d"))

    if has("weekly_position"):
        out.append(_flag("weekly_band", row["weekly_position"], None,
                          row["weekly_position"],
                          {"above": "risk_on", "inside": "neutral", "below": "risk_off"}[row["weekly_position"]]))
    else:
        out.append(unavailable("weekly_band"))

    if has("sma50_vs_200d"):
        value = row["sma50_vs_200d"]
        out.append(_flag("sma50_vs_200d", _round(value, 2), None,
                          "above" if value >= 0 else "below",
                          "risk_on" if value >= 0 else "risk_off"))
    else:
        out.append(unavailable("sma50_vs_200d"))

    if has("alt_vs_200d"):
        value = row["alt_vs_200d"]
        out.append(_flag("alt_vs_200d", _round(value, 2), None,
                          "above" if value >= 0 else "below",
                          "risk_on" if value >= 0 else "risk_off"))
    else:
        out.append(unavailable("alt_vs_200d"))

    if has("eth_btc_30d"):
        value = row["eth_btc_30d"]
        out.append(_flag("eth_btc_30d", _round(value, 2), None,
                          "broadening" if value >= 0 else "narrowing",
                          "risk_on" if value >= 0 else "neutral"))
    else:
        out.append(unavailable("eth_btc_30d"))

    if has("rv_pct"):
        pct = row["rv_pct"]
        rising = row.get("rv_rising")
        flag = "expanding" if pct > 0.80 else "compressed" if pct < 0.20 else "mid"
        if rising is True and flag == "mid":
            flag = "rising"
        out.append(_flag("btc_rv30_pct", _round(row.get("rv_30"), 2), _round(pct, 4),
                          flag, "risk_off" if flag == "expanding" else "neutral"))
    else:
        out.append(unavailable("btc_rv30_pct"))

    if has("dvol_pct"):
        out.append(_flag("dvol_pct", _round(row.get("dvol"), 2), _round(row["dvol_pct"], 4),
                          "high" if row["dvol_pct"] > 0.80 else "low" if row["dvol_pct"] < 0.20 else "mid",
                          "neutral"))
    else:
        out.append(unavailable("dvol_pct"))

    if has("funding_pct"):
        pct = row["funding_pct"]
        out.append(_flag("funding_pct", _round(row.get("funding"), 6), _round(pct, 4),
                          "crowded" if pct > 0.90 else "washed" if pct < 0.20 else "mid",
                          "risk_off" if pct > 0.90 else "capitulation" if pct < 0.20 else "neutral"))
    else:
        out.append(unavailable("funding_pct"))

    if has("oi_flush"):
        out.append(_flag("oi_flush", _round(row.get("oi_change_14d"), 4), None,
                          "flush" if row["oi_flush"] else "none",
                          "capitulation" if row["oi_flush"] else "neutral"))
    else:
        out.append(unavailable("oi_flush"))

    if has("cascade"):
        out.append(_flag("liq_cascade", _round(row.get("liq_share"), 4), None,
                          "cascade" if row["cascade"] else "none",
                          "capitulation" if row["cascade"] else "neutral"))
    else:
        out.append(unavailable("liq_cascade"))

    if has("basis_pct"):
        pct = row["basis_pct"]
        out.append(_flag("basis_pct", _round(row.get("basis"), 4), _round(pct, 4),
                          "steep" if pct > 0.80 else "backwardation" if pct < 0.20 else "mid",
                          "neutral"))
    else:
        out.append(unavailable("basis_pct"))

    if has("breadth_50d"):
        value = row["breadth_50d"]
        flag = "washout" if value < 0.20 else "weak" if value < 0.30 else "broad" if value > 0.50 else "mid"
        out.append(_flag("breadth_above_50d", _round(value, 4), None, flag,
                          "capitulation" if flag == "washout" else "risk_off" if flag == "weak" else "risk_on" if flag == "broad" else "neutral"))
    else:
        out.append(unavailable("breadth_above_50d"))

    if has("drawdown_90d"):
        value = row["drawdown_90d"]
        out.append(_flag("drawdown_90d", _round(value, 2), None,
                          "drawdown" if value < -10 else "near_high",
                          "risk_off" if value < -10 else "neutral"))
    else:
        out.append(unavailable("drawdown_90d"))

    for name in ("stablecoin_supply_30d", "etf_flows_20d", "dxy_30d", "us10y_30d", "btc_ndx_corr_60d"):
        out.append(unavailable(name))
    return out


def readings(panel, market):
    """One row per day of the trailing readings the state machine reads.

    `panel` is the market panel (btc_price, eth_price, alt_price, basis).
    `market` is the derivatives frame from market_measures(). Both are used
    only up to the bar they label.
    """
    close = panel["btc_price"].astype(float)
    frame = pd.DataFrame(index=close.index)
    sma200 = close.rolling(200).mean()
    sma50 = close.rolling(50).mean()
    frame["btc_vs_200d"] = (close / sma200 - 1) * 100
    frame["sma50_vs_200d"] = (sma50 / sma200 - 1) * 100
    position, distance, weeks = weekly_position(close)
    frame["weekly_position"] = position
    frame["weekly_distance"] = distance
    frame["weeks_since_cross"] = weeks
    if "alt_price" in panel:
        alt = panel["alt_price"].astype(float)
        frame["alt_vs_200d"] = (alt / alt.rolling(200).mean() - 1) * 100
        frame["alt_vs_50d"] = (alt / alt.rolling(50).mean() - 1) * 100
        frame["drawdown_alt_90d"] = (alt / alt.rolling(90).max() - 1) * 100
    if "eth_price" in panel:
        ratio = panel["eth_price"].astype(float) / close
        frame["eth_btc_30d"] = ratio.pct_change(30) * 100
    log_ret = np.log(close).diff()
    rv = log_ret.rolling(30).std() * np.sqrt(365) * 100
    frame["rv_30"] = rv
    frame["rv_pct"] = percentile(rv)
    frame["rv_rising"] = rv.diff(10) > 0
    if "dvol_level_btc" in market:
        dvol = market["dvol_level_btc"].reindex(close.index)
        frame["dvol"] = dvol
        frame["dvol_pct"] = percentile(dvol)
    if "funding_oiw_btc" in market:
        funding = market["funding_oiw_btc"].reindex(close.index)
        frame["funding"] = funding
        frame["funding_pct"] = percentile(funding)
    if "basis_btc" in panel:
        basis = panel["basis_btc"].astype(float)
        frame["basis"] = basis
        frame["basis_pct"] = percentile(basis)
    frame["drawdown_90d"] = (close / close.rolling(90).max() - 1) * 100
    frame["drawdown_ath"] = (close / close.expanding().max() - 1) * 100
    return frame


def _state_of(row, breadth):
    """The state the rules name, before hysteresis."""
    above_200 = row.get("btc_vs_200d") is not None and row["btc_vs_200d"] >= 0
    below_200 = row.get("btc_vs_200d") is not None and row["btc_vs_200d"] < 0
    weekly = row.get("weekly_position")
    funding_pct = row.get("funding_pct")
    rv_pct = row.get("rv_pct")
    crowded = funding_pct is not None and funding_pct > 0.90
    vol_expanding = rv_pct is not None and rv_pct > 0.80 and below_200
    capitulation = bool(row.get("oi_flush")) or bool(row.get("cascade"))
    washed = funding_pct is not None and funding_pct < 0.20
    if capitulation and (breadth is not None and breadth < 0.20 or washed):
        return "defensive_after_capitulation"
    if below_200 and weekly == "below":
        return "risk_off_trend_down"
    if weekly == "below" and breadth is not None and breadth < 0.30:
        return "risk_off_distribution"
    if above_200 and weekly == "above" and not crowded and not vol_expanding and (breadth is None or breadth > 0.50):
        return "risk_on_trend"
    if weekly == "above" and row.get("weekly_distance") is not None and row["weekly_distance"] < 2:
        return "risk_on_early"
    return "neutral"


def _rules(row, state):
    fired = []
    if row.get("btc_vs_200d") is not None:
        side = "above" if row["btc_vs_200d"] >= 0 else "below"
        fired.append(f"{side} the 200-day by {abs(row['btc_vs_200d']):.1f} percent")
    if row.get("weekly_position"):
        fired.append(f"weekly band {row['weekly_position']}")
    if row.get("funding_pct") is not None and row["funding_pct"] > 0.90:
        fired.append("funding above its 90th percentile")
    if row.get("oi_flush"):
        fired.append("open interest down more than 25 percent over 14 days")
    if row.get("cascade"):
        fired.append("liquidation cascade")
    if state == "neutral" and not fired:
        fired.append("mixed trend")
    return fired


def dial_of(state, vol_scalar):
    """The middle of the state's band, times the vol scalar, inside 0.5 to 1.3 of it."""
    lo, hi = BANDS[state]
    middle = (lo + hi) / 2
    scaled = middle * vol_scalar
    return round(float(min(max(scaled, middle * VOL_FLOOR), middle * VOL_CAP)), 4)


def vol_scalar_of(rv_pct_value, rv_30):
    """Target vol over realized vol, capped and floored. Missing vol leaves it at 1."""
    if rv_30 is None or not np.isfinite(rv_30) or rv_30 <= 0:
        return 1.0
    return float(min(max(VOL_TARGET / (rv_30 / 100), VOL_FLOOR), VOL_CAP))


def run_states(frame, breadth=None):
    """The state, dial and rules for every day, with the five-day hysteresis.

    `breadth` is a date-indexed share of names above their 50-day. It is
    optional: without it the breadth rules do not fire and the input is
    marked unavailable by the caller.
    """
    states, dials, rules, cuts = [], [], [], []
    current, current_since = None, None
    for i, (stamp, row) in enumerate(frame.iterrows()):
        reading = {k: (None if pd.isna(v) else v) for k, v in row.items()}
        share = None
        if breadth is not None and stamp in breadth.index and pd.notna(breadth.loc[stamp]):
            share = float(breadth.loc[stamp])
        proposed = _state_of(reading, share)
        capitulation = proposed == "defensive_after_capitulation"
        held_for = 0 if current_since is None else (stamp - current_since).days
        if current is None or proposed == current or capitulation or held_for >= HYSTERESIS_DAYS:
            if proposed != current:
                current_since = stamp
            current = proposed
        scalar = vol_scalar_of(reading.get("rv_pct"), reading.get("rv_30"))
        emergency = bool(reading.get("cascade"))
        dial = dial_of(current, scalar)
        if emergency:
            dial = round(dial * 2 / 3, 4)
        states.append(current)
        dials.append(dial)
        rules.append(_rules(reading, current))
        cuts.append(emergency)
    out = frame.copy()
    out["state"] = states
    out["dial"] = dials
    out["rules"] = rules
    out["emergency_cut"] = cuts
    return out


def days_in_state(states):
    """How many bars the last state has held, and the date it changed."""
    last = states.iloc[-1]
    changed = states.index[-1]
    for stamp, value in reversed(list(states.items())):
        if value != last:
            break
        changed = stamp
    return int((states.index[-1] - changed).days) + 1, pd.Timestamp(changed).date().isoformat()


def latest(frame, breadth=None):
    """The live reading: state, dial, rules and the input list for the last day."""
    walked = run_states(frame, breadth)
    row = walked.iloc[-1]
    reading = {k: (None if pd.isna(v) else (bool(v) if isinstance(v, (bool, np.bool_)) else v))
               for k, v in frame.iloc[-1].items()}
    if breadth is not None:
        share = breadth.reindex(frame.index).iloc[-1]
        reading["breadth_50d"] = None if pd.isna(share) else float(share)
    held, changed = days_in_state(walked["state"])
    return {
        "as_of": pd.Timestamp(walked.index[-1]).date().isoformat(),
        "state": row["state"],
        "dial": float(row["dial"]),
        "days_in_state": held,
        "changed_on": changed,
        "inputs": inputs_on(reading),
        "rules_fired": row["rules"],
        "vol_scalar": vol_scalar_of(reading.get("rv_pct"), reading.get("rv_30")),
        "emergency_cut": bool(row["emergency_cut"]),
    }
