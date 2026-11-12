"""C6: breadth family on the names that had data on 2022-09-01.

Pre-registered in research/log.md on 2026-11-10 before this script existed.
The list is today's retained names that already had bars on that date, so the
result is survivor-biased and labelled as such. Does not pull.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

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

UNIVERSE_DATE = pd.Timestamp("2022-09-01", tz="UTC")
SEED = 66


def breadth(ohlcv: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, list[str]]:
    names = [name for name, frame in ohlcv.items()
             if frame.index.min() <= UNIVERSE_DATE and name != "BTC"]
    closes = pd.DataFrame({name: frame["c"] for name, frame in ohlcv.items() if name in names})
    above_50 = closes.gt(closes.rolling(50, min_periods=50).mean())
    above_200 = closes.gt(closes.rolling(200, min_periods=200).mean())
    at_high = closes.eq(closes.rolling(30, min_periods=30).max())
    at_low = closes.eq(closes.rolling(30, min_periods=30).min())
    out = pd.DataFrame({
        "breadth_above_50": above_50.mean(axis=1),
        "breadth_above_200": above_200.mean(axis=1),
        "breadth_high_minus_low": at_high.mean(axis=1) - at_low.mean(axis=1),
    })
    return out, sorted(names)


def run() -> dict:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ohlcv = _names(load_pooled())
    funding = load_funding()
    last = max(frame.index.max() for frame in ohlcv.values())
    series, names = breadth(ohlcv)
    close = ohlcv["BTC"]["c"].rename("close")
    series = series.reindex(close.index)
    rows = []
    base = {}
    for spec in LABELS:
        label = event_label(close, spec)
        base[spec["name"]] = {"BTC": year_caveat(label)}
        if not spec["primary"]:
            continue
        side = spec["side"]
        for name in series.columns:
            rank = rolling_percentile(series[name])
            primary = evaluate(name, side, rank, PRIMARY[side], label, close,
                               funding.get("BTC"), spec["h"], SEED)
            others = [evaluate(name, side, rank, n, label, close, funding.get("BTC"), spec["h"], SEED)
                      for n in NEIGHBOURS[side]]
            primary["asset"] = "BTC"
            primary["neighbours_hold"] = holds(primary, others)
            primary["neighbour_lifts"] = {
                str(other["cut"]): other["score"]["by_period"].get("validation", {}).get("lift")
                for other in others}
            primary["verdict"] = verdict_for(primary, primary["neighbours_hold"])
            rows.append(primary)
    return {
        "today": stamp,
        "panel_end": last.strftime("%Y-%m-%d"),
        "candidate": "c6_breadth",
        "label": "amended T(30, 20) and B(30, 20, 7) on candidate days",
        "horizon_days": HORIZON,
        "universe_date": "2022-09-01",
        "universe": names,
        "survivor_biased": True,
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
    path = ROOT / "results" / f"{result['today']}_c6_breadth.json"
    path.write_text(json.dumps(result))
    print(f"wrote {path} rows={len(result['rows'])} names={len(result['universe'])}")


if __name__ == "__main__":
    main()
