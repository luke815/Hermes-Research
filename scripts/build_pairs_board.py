"""The daily pairs screen, from pair_inputs, into the pairs_board key.

Reads dashboard/keys/pair_inputs.json, which the pair-inputs job already wrote.
It does not pull. The screen is a filter, not a signal.

The spec asks for every ordered pair in three passes: same sector first, then
every name against BTC, ETH and SOL, then cross-sector pairs whose 90-day
correlation is above 0.6. Each pair is scored on the last 90 daily closes.

A row carries the hedge ratio (beta of the long leg to BTC over the beta of
the short leg), the correlation of daily log returns, the Engle-Granger
cointegration p-value on log prices, the half-life of the spread, the window
z and the 20-day z, the annualized net carry, and each leg's 30-day vol and
open interest. bt_sharpe stays null until P3 scores the pair type.

Two lists, 25 rows each. Mean reversion needs a cointegration p below 0.05, a
half-life between 3 and 30 days, an absolute window z above 2, and both legs
above the liquidity floor. Relative strength needs a 30-day return spread in
the top or bottom decile of the screened pairs, with both legs on the same
side of their 50-day average. The cheap leg is the long leg in a reversion
row, and the leader is the long leg in a relative-strength row.

Writes only dashboard/keys/pairs_board.json. The assembler merges and pushes.
"""

import json
import math
import os
import sys

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUTS = os.path.join(ROOT, "dashboard", "keys", "pair_inputs.json")
OUT = os.path.join(ROOT, "dashboard", "keys", "pairs_board.json")
WINDOW = 90
HEDGE_CAP = (0.1, 5.0)
ANCHORS = ("BTC", "ETH", "SOL")
OI_FLOOR = 20_000_000
NOTE = "A filter, not a signal. Backtest pending until P3 writes bt_sharpe."


def _finite(value):
    return value is not None and np.isfinite(value)


def _round(value, places):
    if not _finite(value):
        return None
    return round(float(value), places)


def _log_returns(closes):
    """Daily log returns, empty where either close is missing."""
    out = np.full(len(closes) - 1, np.nan)
    for i in range(1, len(closes)):
        left, right = closes[i - 1], closes[i]
        if _finite(left) and _finite(right) and left > 0 and right > 0:
            out[i - 1] = math.log(right / left)
    return out


def beta(left, right):
    """Slope of left on right, over the bars where both are finite."""
    mask = np.isfinite(left) & np.isfinite(right)
    if int(mask.sum()) < 10:
        return None
    y = left[mask] - left[mask].mean()
    x = right[mask] - right[mask].mean()
    denom = float(np.dot(x, x))
    if denom == 0:
        return None
    return float(np.dot(x, y) / denom)


def correlation(left, right):
    mask = np.isfinite(left) & np.isfinite(right)
    if int(mask.sum()) < 10:
        return None
    value = np.corrcoef(left[mask], right[mask])[0, 1]
    return float(value) if np.isfinite(value) else None


def engle_granger(log_long, log_short):
    """The cointegration p-value of log prices, Engle-Granger with a constant.

    The residual of the log-price regression is regressed on its own lag, and
    the t-stat of that lag is read against the MacKinnon no-trend table. A
    pair with fewer than 30 overlapping bars has no p-value.
    """
    mask = np.isfinite(log_long) & np.isfinite(log_short)
    if int(mask.sum()) < 30:
        return None
    y = log_long[mask]
    x = np.column_stack([np.ones(len(y)), log_short[mask]])
    slope = np.linalg.lstsq(x, y, rcond=None)[0]
    resid = y - x @ slope
    lagged = resid[:-1]
    change = np.diff(resid)
    design = np.column_stack([np.ones(len(lagged)), lagged])
    fit = np.linalg.lstsq(design, change, rcond=None)[0]
    fitted = design @ fit
    sigma = float(np.sqrt(np.sum((change - fitted) ** 2) / (len(change) - 2)))
    spread = float(np.sqrt(np.sum((lagged - lagged.mean()) ** 2)))
    if sigma == 0 or spread == 0:
        return None
    t_stat = float(fit[1] / (sigma / spread))
    return mackinnon_p(t_stat, len(resid))


def mackinnon_p(t_stat, n_obs):
    """MacKinnon (2010) no-trend p-value for two series, with the small-sample term."""
    n = max(int(n_obs), 1)
    adjusted = t_stat - (-3.33613) / n - (-21.2982) / n ** 2
    table = (
        (0.01, -3.95905), (0.025, -3.63815), (0.05, -3.33613),
        (0.10, -3.04686), (0.20, -2.69966), (0.50, -2.13650),
        (0.80, -1.51280), (0.90, -1.21457), (0.95, -0.94100), (0.99, -0.45342),
    )
    if adjusted <= table[0][1]:
        return 0.01
    for (p_lo, t_lo), (p_hi, t_hi) in zip(table, table[1:]):
        if t_hi <= adjusted <= t_lo:
            weight = (adjusted - t_lo) / (t_hi - t_lo)
            return _round(p_lo + weight * (p_hi - p_lo), 4)
    return 0.99


def half_life(spread):
    """Days for the spread to halve, from its lag regression. None if it does not revert."""
    finite = spread[np.isfinite(spread)]
    if len(finite) < 20:
        return None
    mean = float(finite.mean())
    lagged = spread[:-1] - mean
    change = np.diff(spread)
    mask = np.isfinite(lagged) & np.isfinite(change)
    if int(mask.sum()) < 10:
        return None
    phi = beta(change[mask], lagged[mask])
    if phi is None or not -1 < phi < 0:
        return None
    return float(-math.log(2) / math.log(1 + phi))


def zscore(spread, window):
    finite = spread[np.isfinite(spread)][-window:]
    if len(finite) < min(window, 20):
        return None
    sd = float(finite.std(ddof=1))
    if sd == 0:
        return None
    return float((finite[-1] - finite.mean()) / sd)


def prepare(names, dates):
    """Per-name arrays the screen reads, aligned to the date list."""
    btc = np.array(names["BTC"]["close"], dtype=float) if "BTC" in names else None
    btc_ret = _log_returns(btc) if btc is not None else None
    out = {}
    for coin, row in names.items():
        closes = np.array(row["close"], dtype=float)
        if np.isfinite(closes[-WINDOW:]).sum() < WINDOW * 0.8:
            continue
        log_px = np.full(len(closes), np.nan)
        positive = np.isfinite(closes) & (closes > 0)
        log_px[positive] = np.log(closes[positive])
        returns = _log_returns(closes)
        tail = closes[-50:]
        tail = tail[np.isfinite(tail)]
        last = closes[-1] if _finite(closes[-1]) else None
        earlier = closes[-31] if len(closes) > 31 and _finite(closes[-31]) else None
        out[coin] = {
            "log": log_px,
            "ret": returns,
            "beta": beta(returns, btc_ret) if btc_ret is not None and coin != "BTC" else 1.0,
            "above50": bool(last > float(tail.mean())) if last and len(tail) else None,
            "ret30": (last / earlier - 1) if last and earlier else None,
            "vol_30": row.get("vol_30"),
            "oi_usd": row.get("oi_usd"),
            "funding_7d": row.get("funding_7d"),
            "sector": row.get("sector") or "",
        }
    return out


def hedge_ratio(long_leg, short_leg):
    """Beta-neutral to BTC, capped, and 1 when the short beta is too small to divide."""
    if not _finite(long_leg["beta"]) or not _finite(short_leg["beta"]) or short_leg["beta"] <= 0.05:
        return 1.0
    return float(min(HEDGE_CAP[1], max(HEDGE_CAP[0], long_leg["beta"] / short_leg["beta"])))


def carry(long_leg, short_leg, hedge):
    """Annualized net carry, percent of gross, from the 7-day funding print."""
    if not _finite(long_leg["funding_7d"]) or not _finite(short_leg["funding_7d"]):
        return None
    return ((short_leg["funding_7d"] * hedge) - long_leg["funding_7d"]) * 3 * 365 / (1 + hedge)


def score_pair(long_name, short_name, legs):
    """One ordered pair, or None when the window is too thin to score."""
    long_leg, short_leg = legs[long_name], legs[short_name]
    corr = correlation(long_leg["ret"][-WINDOW:], short_leg["ret"][-WINDOW:])
    if corr is None:
        return None
    hedge = hedge_ratio(long_leg, short_leg)
    spread = long_leg["log"] - hedge * short_leg["log"]
    window = spread[-WINDOW:]
    if np.isfinite(window).sum() < 60:
        return None
    return {
        "long": long_name, "short": short_name,
        "sector": long_leg["sector"] if long_leg["sector"] == short_leg["sector"] else "",
        "z": _round(zscore(window, WINDOW), 2),
        "z20": _round(zscore(window, 20), 2),
        "half_life": _round(half_life(window), 1),
        "coint_p": engle_granger(long_leg["log"][-WINDOW:], short_leg["log"][-WINDOW:]),
        "corr": _round(corr, 2),
        "hedge": _round(hedge, 2),
        "carry": _round(carry(long_leg, short_leg, hedge), 1),
        "oi_long": long_leg["oi_usd"], "oi_short": short_leg["oi_usd"],
        "vol_long": long_leg["vol_30"], "vol_short": short_leg["vol_30"],
        "ret30_gap": _round((long_leg["ret30"] or 0) - (short_leg["ret30"] or 0), 4)
        if _finite(long_leg["ret30"]) and _finite(short_leg["ret30"]) else None,
        "same_trend": long_leg["above50"] is not None and long_leg["above50"] == short_leg["above50"],
        "bt_sharpe": None,
    }


def _same_coin(left, right):
    """A prefixed listing of the same coin (XYZ:SNDK against SNDK) is one coin."""
    return left.split(":")[-1] == right.split(":")[-1]


def candidates(legs):
    """The three passes, in the spec's order, each ordered pair once."""
    names = sorted(legs)
    seen = set()
    ordered = []

    def add(left, right):
        if left == right or _same_coin(left, right) or left not in legs or right not in legs:
            return
        key = (left, right)
        if key in seen:
            return
        seen.add(key)
        ordered.append(key)

    by_sector = {}
    for name in names:
        by_sector.setdefault(legs[name]["sector"], []).append(name)
    for sector, group in by_sector.items():
        if not sector:
            continue
        for left in group:
            for right in group:
                add(left, right)
    for name in names:
        for anchor in ANCHORS:
            add(name, anchor)
            add(anchor, name)
    returns = {name: legs[name]["ret"][-WINDOW:] for name in names}
    for i, left in enumerate(names):
        for right in names[i + 1:]:
            corr = correlation(returns[left], returns[right])
            if corr is not None and corr > 0.6:
                add(left, right)
                add(right, left)
    return ordered


def liquid(row):
    return (row["oi_long"] or 0) >= OI_FLOOR and (row["oi_short"] or 0) >= OI_FLOOR


def _dedupe(rows):
    """One direction per pair. The reversed order is the same pair, not a second one."""
    seen = set()
    out = []
    for row in rows:
        key = tuple(sorted((row["long"], row["short"])))
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def reversion_rows(rows):
    kept = [row for row in rows if liquid(row)
            and row["coint_p"] is not None and row["coint_p"] < 0.05
            and row["half_life"] is not None and 3 <= row["half_life"] <= 30
            and row["z"] is not None and abs(row["z"]) > 2]
    kept.sort(key=lambda row: abs(row["z"]), reverse=True)
    return [_oriented(row) for row in _dedupe(kept)[:25]]


def _oriented(row):
    """The cheap leg is the long leg. A positive z means the first leg is rich."""
    if row["z"] is not None and row["z"] > 0:
        return _swap(row)
    return row


def _swap(row):
    swapped = dict(row)
    swapped["long"], swapped["short"] = row["short"], row["long"]
    swapped["oi_long"], swapped["oi_short"] = row["oi_short"], row["oi_long"]
    swapped["vol_long"], swapped["vol_short"] = row["vol_short"], row["vol_long"]
    for key in ("z", "z20", "ret30_gap"):
        if swapped[key] is not None:
            swapped[key] = _round(-swapped[key], 4 if key == "ret30_gap" else 2)
    if swapped["hedge"]:
        swapped["hedge"] = _round(1 / swapped["hedge"], 2)
    return swapped


def strength_rows(rows):
    """Top and bottom decile of the 30-day gap, both legs trending the same way."""
    pool = [row for row in rows if row["same_trend"] and row["ret30_gap"] is not None and liquid(row)]
    if len(pool) < 10:
        return []
    gaps = sorted(row["ret30_gap"] for row in pool)
    lo = gaps[max(len(gaps) // 10 - 1, 0)]
    hi = gaps[-(len(gaps) // 10)]
    kept = [row for row in pool if row["ret30_gap"] >= hi or row["ret30_gap"] <= lo]
    kept.sort(key=lambda row: abs(row["ret30_gap"]), reverse=True)
    out = []
    for row in _dedupe(kept)[:25]:
        oriented = _swap(row) if row["ret30_gap"] < 0 else row
        oriented = dict(oriented)
        oriented["type"] = "relative_strength"
        out.append(oriented)
    return out


def screen(payload):
    """The key. as_of is the pair-inputs date, never typed."""
    legs = prepare(payload["names"], payload["dates"])
    rows = []
    for left, right in candidates(legs):
        row = score_pair(left, right, legs)
        if row is not None:
            rows.append(row)
    reversion = reversion_rows(rows)
    for row in reversion:
        row["type"] = "reversion"
    strength = strength_rows(rows)
    return {
        "as_of": payload["as_of"],
        "note": NOTE,
        "screened": len(rows),
        "names": len(legs),
        "rows": [_public(row) for row in reversion + strength],
    }


def _public(row):
    return {key: row[key] for key in (
        "long", "short", "type", "sector", "z", "z20", "half_life", "coint_p",
        "corr", "hedge", "carry", "oi_long", "oi_short", "vol_long", "vol_short",
        "bt_sharpe")}


def main():
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from dashboard_io import write_key
    from regime_tester.results_io import write_result
    payload = json.load(open(INPUTS))
    board = screen(payload)
    write_key(OUT, board)
    types = {}
    for row in board["rows"]:
        types[row["type"]] = types.get(row["type"], 0) + 1
    summary = {"as_of": board["as_of"], "screened": board["screened"],
               "names": board["names"], "rows": len(board["rows"]), "by_type": types}
    path = write_result("p2_pairs_board", summary, inputs=["dashboard/keys/pair_inputs.json"])
    print(json.dumps(summary))
    print(path)


if __name__ == "__main__":
    main()
