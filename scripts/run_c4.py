"""C4: trend exhaustion family as events.

Pre-registered in research/log.md on 2026-11-10 before this script existed.
Reads the retained Coinalyze file. Does not pull and does not write the panel.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from regime_tester.cycle_score import (
    HORIZON,
    LABELS,
    NEIGHBOURS,
    PRIMARY,
    ROOT,
    clean,
    evaluate,
    event_label,
    holds,
    load_funding,
    load_pooled,
    verdict_for,
    year_caveat,
)
from regime_tester.events import rolling_percentile
from regime_tester.indicators import mayer_multiple, pi_cycle

ASSETS = ("BTC", "ETH", "SOL")
SEED = 64


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window, min_periods=window).mean()
    loss = (-delta.clip(upper=0)).rolling(window, min_periods=window).mean()
    return (100 - 100 / (1 + gain / loss.replace(0, np.nan))).rename("rsi_14")


def weekly_band_state(close: pd.Series) -> pd.Series:
    """1 above the weekly band, 0 inside, -1 below. The band uses closed weeks only."""
    weekly = close.resample("W-SUN").last().dropna()
    sma = weekly.rolling(20, min_periods=20).mean()
    ema = weekly.ewm(span=21, adjust=False).mean()
    band = pd.DataFrame({"lo": np.minimum(sma, ema), "hi": np.maximum(sma, ema)})
    band = band.shift(1).reindex(close.index, method="ffill")
    state = pd.Series(0.0, index=close.index)
    state = state.mask(close > band["hi"], 1.0).mask(close < band["lo"], -1.0)
    return state.where(band["hi"].notna())


def factors_for(frame: pd.DataFrame) -> dict[str, pd.Series]:
    close = frame["c"]
    out = {
        "mayer_multiple": mayer_multiple(close),
        "pi_cycle_distance": close.rolling(111, min_periods=111).mean() - 2 * close.rolling(350, min_periods=350).mean(),
        "pi_cycle_cross": pi_cycle(close),
        "rsi_14": rsi(close),
        "ret_30": close.pct_change(30),
        "acceleration": close.pct_change(14) - close.pct_change(14).shift(14),
        "weekly_band_state": weekly_band_state(close),
    }
    price_high = close.rolling(20, min_periods=20).max()
    rsi_high = out["rsi_14"].rolling(20, min_periods=20).max()
    divergence = (close.eq(price_high) & out["rsi_14"].lt(rsi_high.shift(1))).astype(float)
    out["rsi_divergence"] = divergence
    return out


def run() -> dict:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ohlcv = _names(load_pooled())
    funding = load_funding()
    last = max(frame.index.max() for frame in ohlcv.values())
    rows = []
    base = {}
    for asset in ASSETS:
        frame = ohlcv[asset]
        close = frame["c"].rename("close")
        built = factors_for(frame)
        for spec in LABELS:
            label = event_label(close, spec)
            base.setdefault(spec["name"], {})[asset] = year_caveat(label)
            if not spec["primary"]:
                continue
            side = spec["side"]
            for name, series in built.items():
                lagged = series.shift(1)
                if name == "weekly_band_state":
                    rank = lagged
                    cut = 1.0 if side == "top" else -1.0
                    neighbours = []
                elif name == "pi_cycle_cross" or name == "rsi_divergence":
                    rank = lagged.fillna(0.0)
                    cut = 1.0
                    neighbours = []
                else:
                    rank = rolling_percentile(series)
                    cut = PRIMARY[side]
                    neighbours = list(NEIGHBOURS[side])
                primary = evaluate(name, side, rank, cut, label, close, funding.get(asset), spec["h"], SEED)
                others = [evaluate(name, side, rank, n, label, close, funding.get(asset), spec["h"], SEED)
                          for n in neighbours]
                primary["asset"] = asset
                primary["neighbours_hold"] = holds(primary, others) if others else None
                primary["neighbour_lifts"] = {
                    str(other["cut"]): other["score"]["by_period"].get("validation", {}).get("lift")
                    for other in others}
                primary["verdict"] = verdict_for(primary, primary["neighbours_hold"] is not False)
                rows.append(primary)
    return {
        "today": stamp,
        "panel_end": last.strftime("%Y-%m-%d"),
        "candidate": "c4_trend_exhaustion",
        "label": "amended T(30, 20) and B(30, 20, 7) on candidate days",
        "horizon_days": HORIZON,
        "base_rates": base,
        "rows": rows,
    }



def _names(ohlcv):
    """Map the short asset names the scripts use onto the panel's filenames."""
    aliases = {"BTC": "binance_BTCUSDT", "ETH": "binance_ETHUSDT", "SOL": "binance_SOLUSDT"}
    return {aliases.get(name, name): frame for name, frame in ohlcv.items()} | {
        short: ohlcv[full] for short, full in aliases.items() if full in ohlcv}

def main() -> None:
    result = clean(run())
    path = ROOT / "results" / f"{result['today']}_c4_trend_exhaustion.json"
    path.write_text(json.dumps(result))
    print(f"wrote {path} rows={len(result['rows'])}")


if __name__ == "__main__":
    main()
