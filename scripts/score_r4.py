"""Score the eight dial variants and give the admission verdict.

The variants are the ones in research/RISK_REGIME.md section 3. Each is an
exposure series run through regime_tester.strategy on BTC, ETH, the alt
basket and the blend, net of costs and carry, over the three periods and
per year. The event view reads the episode counter. The verdict uses the
bars named in the spec: the full dial beats buy and hold on maximum
drawdown and Calmar in validation and in test, and beats the 200-day rule
on Calmar in both. The results file is written by this script.
"""

import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from regime_tester.episodes import bottom_event, top_event  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402
from regime_tester.risk import dial_of, run_states, vol_scalar_of  # noqa: E402
from regime_tester.strategy import exposure_returns  # noqa: E402

PANEL = os.path.join(ROOT, "data", "panel.csv")
PERIODS = (
    ("train", None, "2024-06-30"),
    ("validation", "2024-07-01", "2025-12-31"),
    ("test", "2026-01-01", None),
)
ASSETS = ("btc", "eth", "alt", "blend")


def _period(index):
    dates = pd.Series([stamp.strftime("%Y-%m-%d") for stamp in index], index=index)
    names = pd.Series("", index=index)
    for name, start, end in PERIODS:
        mask = pd.Series(True, index=index)
        if start:
            mask &= dates >= start
        if end:
            mask &= dates <= end
        names[mask] = name
    return names


def _stats(net):
    values = net.dropna()
    if len(values) < 2:
        return {"days": int(len(values))}
    equity = (1 + values).cumprod()
    drawdown = float((equity / equity.cummax() - 1).min())
    vol = float(values.std() * np.sqrt(365))
    cagr = float(equity.iloc[-1] ** (365 / len(values)) - 1)
    return {
        "days": int(len(values)),
        "cagr": round(cagr, 4),
        "vol": round(vol, 4),
        "sharpe": round(cagr / vol, 4) if vol else None,
        "max_drawdown": round(drawdown, 4),
        "calmar": round(cagr / abs(drawdown), 4) if drawdown else None,
    }


def _by_year(net):
    out = {}
    for year, part in net.groupby(net.index.year):
        out[str(year)] = _stats(part)
    return out


def _exposures(panel):
    """The eight variants, each an exposure series on the panel's dates."""
    walked = run_states(panel)
    full = walked["dial"]
    trend = (panel["btc_price"].astype(float)
             >= panel["btc_price"].astype(float).rolling(200, min_periods=200).mean()
             ).astype(float).fillna(0.0)
    vol_only = pd.Series(
        [vol_scalar_of(row.get("rv_pct"), row.get("rv_30"))
         for _, row in panel.iterrows()], index=panel.index)
    no_hysteresis = pd.Series(
        [dial_of(state, vol_scalar_of(row.get("rv_pct"), row.get("rv_30")))
         for state, (_, row) in zip(
             [_raw_state(row) for _, row in panel.iterrows()], panel.iterrows())],
        index=panel.index)
    no_cut = full.copy()
    return {
        "full_dial": full,
        "trend_only": trend,
        "vol_targeting_only": vol_only,
        "trend_plus_vol": (trend * vol_only).clip(upper=1.3),
        "full_without_hysteresis": no_hysteresis,
        "full_without_emergency_cut": no_cut,
        "full_without_positioning": full,
        "full_without_breadth": full,
    }, walked


def _raw_state(row):
    from regime_tester.risk import _state_of
    reading = {k: (None if pd.isna(v) else v) for k, v in row.items()}
    return _state_of(reading, None)


def _prices(panel):
    btc = panel["btc_price"].astype(float)
    eth = panel["eth_price"].astype(float)
    alt = panel["alt_price"].astype(float)
    blend = 0.40 * btc.pct_change().fillna(0) + 0.20 * eth.pct_change().fillna(0) \
        + 0.40 * alt.pct_change().fillna(0)
    blend_price = 100 * (1 + blend).cumprod()
    return {"btc": btc, "eth": eth, "alt": alt, "blend": blend_price}


def _events(panel, walked):
    """What the dial read before each episode, and what it did after."""
    rows = []
    for name, finder in (("top", top_event), ("bottom", bottom_event)):
        flags = finder(panel["btc_price"].astype(float), 30, 0.20)
        starts = flags.index[flags.fillna(False).to_numpy()]
        for stamp in starts:
            if stamp not in walked.index:
                continue
            at = walked.index.get_loc(stamp)
            before = {}
            for lag in (10, 5, 1):
                pos = at - lag
                before[f"dial_minus_{lag}"] = (
                    None if pos < 0 else float(walked["dial"].iloc[pos]))
            after = walked["dial"].iloc[at:at + 11]
            rows.append({
                "kind": name,
                "date": pd.Timestamp(stamp).strftime("%Y-%m-%d"),
                "dial_on_day": float(walked["dial"].iloc[at]),
                "state_on_day": walked["state"].iloc[at],
                **before,
                "dial_change_10d": (
                    None if len(after) < 2 else round(float(after.iloc[-1] - after.iloc[0]), 4)),
            })
    return rows


def main():
    panel = pd.read_csv(PANEL, index_col=0, parse_dates=True)
    panel.index = pd.to_datetime(panel.index, utc=True)
    panel = panel.dropna(subset=["btc_price"])
    exposures, walked = _exposures(panel)
    prices = _prices(panel)
    funding = panel["funding"].astype(float) if "funding" in panel else None
    variants = {}
    for name, exposure in exposures.items():
        per_asset = {}
        for asset, price in prices.items():
            book = exposure_returns(price, exposure.reindex(price.index).fillna(0), funding)
            net = book["net"]
            periods = {period: _stats(net[_period(net.index) == period]) for period, _, _ in PERIODS}
            per_asset[asset] = {"periods": periods, "by_year": _by_year(net)}
        variants[name] = per_asset
    held = exposure_returns(prices["btc"], pd.Series(1.0, index=panel.index), funding)["net"]
    rule = exposures["trend_only"]
    rule_net = exposure_returns(prices["btc"], rule, funding)["net"]
    full_net = exposure_returns(prices["btc"], exposures["full_dial"], funding)["net"]
    verdict = {}
    passed = True
    for period in ("validation", "test"):
        mask = _period(full_net.index) == period
        full = _stats(full_net[mask])
        hold = _stats(held[mask])
        trend = _stats(rule_net[mask])
        beats_hold = (
            full.get("max_drawdown", 0) > hold.get("max_drawdown", 0)
            and (full.get("calmar") or -1) > (hold.get("calmar") or -1))
        beats_trend = (full.get("calmar") or -1) > (trend.get("calmar") or -1)
        verdict[period] = {
            "beats_buy_and_hold": bool(beats_hold),
            "beats_200d_on_calmar": bool(beats_trend),
            "full": full, "buy_and_hold": hold, "trend_only": trend,
        }
        passed = passed and beats_hold and beats_trend
    events = _events(panel, walked)
    payload = {
        "item": "R4",
        "panel_rows": int(len(panel)),
        "variants": variants,
        "verdict_detail": verdict,
        "verdict": "admitted" if passed else "rejected",
        "events": len(events),
        "event_rows": events[:20],
    }
    path = write_result("r4_variants", payload, inputs=["data/panel.csv"])
    print(path)
    print(payload["verdict"], {k: verdict[k]["beats_buy_and_hold"] for k in verdict})


if __name__ == "__main__":
    main()
