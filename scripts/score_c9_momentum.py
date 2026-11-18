"""C9. Cross-sectional momentum on the point-in-time panel.

Pre-registered before any number is read from the output:

  Signal: trailing close[t-1] / close[t-1-lookback] - 1, lookbacks 14 and 28
  days. The bar being scored is excluded, so the signal uses only closes
  that had already printed.
  Rebalance: every 7th date, the same dates in every period.
  Book: long the top decile, short the bottom decile, equal weight, on the
  names listed that date in the span files. A name whose span has ended is
  absent. One row per coin per date: when a coin is listed on more than one
  exchange, the file with the longer history is kept.
  Forward return: close[t+horizon] / close[t] - 1, horizons 7, 14 and 28.
  The rebalance stride equals the shortest horizon, so the reported sample
  does not overlap.
  Costs: per leg, the thin-tier round trip from regime_tester.costs, charged
  to both the long and the short. Open interest is not in this panel for the
  live names, so every leg takes the thin tier and the result says so.
  Carry: funding inside the holding window, signed by the side. A name with
  no funding file leaves its carry missing, and a date where any held name
  has a missing carry is dropped rather than treated as zero.
  Periods: train through 2024-06-30, validation 2024-07-01 to 2025-12-31,
  test from 2026-01-01. A t-stat is the mean spread over its standard error
  on the non-overlapping dates. Below 40 dates is insufficient.

The panel is data/panel_xs, which holds the stopped names. It is not
data/panel_xs_laevitas, whose catalogue drops the delisted names.
"""

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regime_tester.costs import round_trip
from regime_tester.periods import PERIODS, assign_period
from regime_tester.pit import span_rows

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs")
LOOKBACKS = (14, 28)
HORIZONS = (7, 14, 28)
STRIDE = 7
THIN = round_trip(None)


def base_of(symbol):
    name = symbol.upper()
    for suffix in ("-USDT-SWAP", "USDT", "-USDT"):
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return name


def load_panel():
    """One frame per coin, the longest file when several exchanges list it."""
    universe = span_rows()
    chosen = {}
    for row in universe.itertuples(index=False):
        path = os.path.join(PANEL, f"{row.exchange}_{row.symbol}.csv")
        if not os.path.exists(path):
            continue
        coin = base_of(row.symbol)
        span = (row.listed_to, path)
        if coin not in chosen or span > chosen[coin][0]:
            chosen[coin] = (span, row.exchange, row.symbol, row.listed_from, row.listed_to)
    frames = {}
    for coin, (span, exchange, symbol, listed_from, listed_to) in chosen.items():
        frame = pd.read_csv(span[1], usecols=lambda c: c in ("date", "close", "funding_rate"))
        frame["date"] = pd.to_datetime(frame["date"], utc=True).dt.normalize()
        frame = frame.drop_duplicates("date").set_index("date").sort_index()
        start = pd.Timestamp(listed_from, tz="UTC")
        end = pd.Timestamp(listed_to, tz="UTC")
        frame = frame[(frame.index >= start) & (frame.index <= end)]
        if frame.empty or "close" not in frame:
            continue
        frames[coin] = frame
    return frames, len(universe)


def book(frames):
    """Close, lagged momentum and forward net return, aligned on one calendar."""
    closes = {coin: frame["close"].astype(float) for coin, frame in frames.items()}
    close = pd.DataFrame(closes).sort_index()
    funding = pd.DataFrame({
        coin: frame["funding_rate"] if "funding_rate" in frame else np.nan
        for coin, frame in frames.items()
    }).reindex(close.index)
    out = {"close": close, "funding": funding}
    for lookback in LOOKBACKS:
        out[f"mom_{lookback}"] = close.shift(1) / close.shift(1 + lookback) - 1
    for horizon in HORIZONS:
        gross = close.shift(-horizon) / close - 1
        daily = funding / 100.0
        carry = pd.DataFrame({
            coin: daily[coin].rolling(horizon).sum().shift(-(horizon - 1))
            for coin in daily
        })
        out[f"gross_{horizon}"] = gross
        out[f"carry_{horizon}"] = carry
    return out


def spread_on(signal, gross, carry, horizon):
    """Long top decile, short bottom decile, net of two thin round trips.

    A date is dropped when either decile is empty or any held name is missing
    its carry. The carry of a short is received, so it is subtracted with the
    opposite sign.
    """
    both = signal.notna() & gross.notna()
    rows = []
    for date in signal.index[::STRIDE]:
        live = both.loc[date]
        if int(live.sum()) < 20:
            continue
        ranks = signal.loc[date][live].rank(pct=True)
        top = ranks[ranks >= 0.9].index
        bottom = ranks[ranks <= 0.1].index
        if len(top) == 0 or len(bottom) == 0:
            continue
        # A name with no funding file cannot be charged a carry, and treating
        # that as zero would understate the cost. Both deciles are restricted
        # to names whose carry is known. A decile that falls below ten names
        # is dropped and counted, not scored.
        top = [name for name in top if pd.notna(carry.loc[date, name])]
        bottom = [name for name in bottom if pd.notna(carry.loc[date, name])]
        if len(top) < 10 or len(bottom) < 10:
            rows.append({"date": date, "dropped_missing_carry": True,
                         "spread": np.nan, "gross": np.nan, "names": int(live.sum())})
            continue
        long_net = gross.loc[date, top] - THIN - carry.loc[date, top]
        short_net = -gross.loc[date, bottom] - THIN + carry.loc[date, bottom]
        rows.append({
            "date": date,
            "spread": float(long_net.mean() + short_net.mean()),
            "gross": float(gross.loc[date, top].mean() - gross.loc[date, bottom].mean()),
            "names": int(live.sum()),
            "dropped_missing_carry": False,
        })
    return pd.DataFrame(rows).set_index("date") if rows else pd.DataFrame()


def summarize(frame):
    kept = frame[~frame["dropped_missing_carry"]] if not frame.empty else frame
    period = assign_period(kept.index) if not kept.empty else pd.Series(dtype="object")
    out = {}
    for name, _, _ in PERIODS:
        part = kept[period == name]["spread"] if not kept.empty else pd.Series(dtype=float)
        values = part.dropna().to_numpy()
        n = int(len(values))
        mean = float(values.mean()) if n else None
        se = float(values.std(ddof=1) / np.sqrt(n)) if n > 1 else None
        out[name] = {
            "n": n,
            "mean_spread": mean,
            "t": float(mean / se) if mean is not None and se else None,
            "hit_rate": float((values > 0).mean()) if n else None,
        }
    years = []
    if not kept.empty:
        for year, part in kept.groupby(kept.index.year):
            values = part["spread"].dropna().to_numpy()
            years.append({"year": int(year), "n": int(len(values)),
                          "mean_spread": float(values.mean()) if len(values) else None})
    return {
        "dates_scored": int((~frame["dropped_missing_carry"]).sum()) if not frame.empty else 0,
        "dates_dropped_missing_carry": int(frame["dropped_missing_carry"].sum()) if not frame.empty else 0,
        "periods": out,
        "years": years,
    }


def verdict_for(cells):
    """Kept only when every cell holds its sign in validation and in test."""
    signs = []
    for cell in cells:
        for period in ("validation", "test"):
            mean = cell["periods"][period]["mean_spread"]
            n = cell["periods"][period]["n"]
            if mean is None or n < 40:
                return "insufficient"
            signs.append(mean > 0)
    if all(signs) or not any(signs):
        return "recorded"
    return "rejected"


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    frames, universe_rows = load_panel()
    built = book(frames)
    cells = []
    for lookback in LOOKBACKS:
        for horizon in HORIZONS:
            scored = spread_on(
                built[f"mom_{lookback}"], built[f"gross_{horizon}"],
                built[f"carry_{horizon}"], horizon)
            cells.append({
                "lookback": lookback, "horizon": horizon, "stride": STRIDE,
                **summarize(scored),
            })
    payload = {
        "date": today,
        "item": "C9",
        "panel": "data/panel_xs",
        "universe_rows": universe_rows,
        "coins_with_a_file": len(frames),
        "cost_per_leg": THIN,
        "cost_note": "thin tier on every leg; open interest is absent for the live names",
        "cells": cells,
        "verdict": verdict_for(cells),
    }
    out = os.path.join(ROOT, "results", f"{today}_c9_momentum.json")
    json.dump(payload, open(out, "w"), indent=1)
    print(out)
    print(json.dumps({"coins": len(frames), "verdict": payload["verdict"],
                      "cells": [(c["lookback"], c["horizon"], c["dates_scored"],
                                 c["dates_dropped_missing_carry"]) for c in cells]}))


if __name__ == "__main__":
    main()
