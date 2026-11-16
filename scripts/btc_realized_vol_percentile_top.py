"""btc_realized_vol_percentile_top, pre-registered in research/log.md on 2026-11-16.

The factor is the 30-day standard deviation of log close-to-close returns,
annualized by the square root of 365, lagged one bar. The extreme is at or
above its trailing one-year 90th percentile, neighbours at the 85th and the
95th. Scored against the amended top event. Reads the retained Coinalyze
file. Does not pull and does not write the panel.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from regime_tester.cycle_score import (  # noqa: E402
    clean,
    evaluate,
    event_label,
    holds,
    train_val_episodes,
    verdict_for,
    year_caveat,
)
from regime_tester.events import rolling_percentile  # noqa: E402

SEED = 64
WINDOW = 30
PRIMARY = 0.90
NEIGHBOURS = (0.85, 0.95)
ASSETS = ("BTC", "ETH")
LABELS = (
    {"name": "top_30_20", "side": "top", "kind": "top",
     "h": 30, "x": 0.20, "primary": True},
    {"name": "top_20_15", "side": "top", "kind": "top",
     "h": 20, "x": 0.15, "primary": False},
    {"name": "top_60_30", "side": "top", "kind": "top",
     "h": 60, "x": 0.30, "primary": False},
)


def load_closes() -> dict[str, pd.Series]:
    blob = json.loads((ROOT / "data" / "raw" / "coinalyze_ohlcv-history.json").read_text())
    names = {symbol: asset for asset, symbol in blob["symbols"].items()}
    out = {}
    for entry in blob["data"]:
        if entry["symbol"] not in names or names[entry["symbol"]] not in ASSETS:
            continue
        frame = pd.DataFrame(entry["history"])
        index = pd.to_datetime(frame["t"], unit="s", utc=True).dt.normalize()
        series = pd.to_numeric(frame["c"], errors="coerce")
        series.index = index
        out[names[entry["symbol"]]] = series[~series.index.duplicated(keep="last")].sort_index()
    return out


def load_funding() -> dict[str, pd.Series]:
    blob = json.loads((ROOT / "data" / "raw" / "coinalyze_funding-rate-history.json").read_text())
    names = {symbol: asset for asset, symbol in blob["symbols"].items()}
    out = {}
    for entry in blob["data"]:
        if entry["symbol"] not in names or names[entry["symbol"]] not in ASSETS:
            continue
        frame = pd.DataFrame(entry["history"])
        index = pd.to_datetime(frame["t"], unit="s", utc=True).dt.normalize()
        series = pd.to_numeric(frame["c"], errors="coerce")
        series.index = index
        out[names[entry["symbol"]]] = series[~series.index.duplicated(keep="last")].sort_index()
    return out


def realized_vol(close: pd.Series) -> pd.Series:
    """30-day realized vol, annualized. The first 30 bars stay empty."""
    vol = np.log(close).diff().rolling(WINDOW, min_periods=WINDOW).std() * np.sqrt(365)
    return vol.rename("rv_30")


def lookahead_holds(close: pd.Series) -> bool:
    """Perturb every price after day t. The factor and its rank at t must not move."""
    t = len(close) // 2
    factor = realized_vol(close)
    rank = rolling_percentile(factor)
    perturbed = close.copy()
    perturbed.iloc[t + 1:] = perturbed.iloc[t + 1:] * 3
    again_factor = realized_vol(perturbed)
    again_rank = rolling_percentile(again_factor)
    return bool(factor.iloc[:t + 1].equals(again_factor.iloc[:t + 1])) and bool(
        rank.iloc[:t + 1].equals(again_rank.iloc[:t + 1]))


def score_asset(asset: str, close: pd.Series, funding: pd.Series | None) -> tuple[list, dict]:
    factor = realized_vol(close)
    rank = rolling_percentile(factor)
    rows = []
    base = {}
    for spec in LABELS:
        label = event_label(close, spec)
        base[spec["name"]] = year_caveat(label)
        scored = []
        for cut in (PRIMARY,) + NEIGHBOURS:
            row = evaluate("rv_30", spec["side"], rank, cut, label, close,
                           funding, spec["h"], SEED)
            row["asset"] = asset
            row["label"] = spec["name"]
            row["transform"] = "percentile_1y"
            row["primary"] = cut == PRIMARY
            scored.append(row)
        primary, neighbours = scored[0], scored[1:]
        primary["neighbours_hold"] = holds(primary, neighbours) if spec["primary"] else None
        primary["train_val_fires"] = train_val_episodes(primary)
        if spec["primary"]:
            primary["verdict"] = verdict_for(primary, bool(primary["neighbours_hold"]))
        else:
            primary["verdict"] = "reported"
        rows.append(primary)
        for other in neighbours:
            other["verdict"] = "neighbour"
            other["neighbours_hold"] = None
            other["train_val_fires"] = train_val_episodes(other)
            rows.append(other)
    return rows, base


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    closes = load_closes()
    funding = load_funding()
    last = max(series.index.max() for series in closes.values())
    age = (pd.Timestamp(stamp, tz="UTC") - last).days
    print(f"today={stamp} panel_end={last.strftime('%Y-%m-%d')} age={age}d", flush=True)
    if age > 2:
        sys.exit(f"stale: last close {last.date()} is {age} days behind {stamp}")
    missing = [asset for asset in ASSETS if asset not in closes]
    if missing:
        sys.exit(f"missing closes: {missing}")

    rows = []
    base = {}
    lookahead = {}
    for asset in ASSETS:
        asset_rows, asset_base = score_asset(
            asset, closes[asset], funding.get(asset))
        rows.extend(asset_rows)
        base[asset] = asset_base
        lookahead[asset] = lookahead_holds(closes[asset])
        print(f"{asset} rows={len(asset_rows)} lookahead={lookahead[asset]}", flush=True)
    if not all(lookahead.values()):
        sys.exit(f"lookahead failed: {lookahead}")

    out = {
        "today": stamp,
        "panel_end": last.strftime("%Y-%m-%d"),
        "age_days": int(age),
        "candidate": "btc_realized_vol_percentile_top",
        "rule": "30-day realized vol of log returns, lagged one bar, at or above "
                "its trailing one-year percentile",
        "primary_cut": PRIMARY,
        "neighbours": list(NEIGHBOURS),
        "label": "amended T(30, 20) on candidate days; T(20, 15) and T(60, 30) reported",
        "horizon_days": 30,
        "assets": list(ASSETS),
        "lookahead_holds": lookahead,
        "base_rates": base,
        "rows": rows,
    }
    path = ROOT / "results" / f"{stamp}_btc_realized_vol_percentile_top.json"
    path.write_text(json.dumps(clean(out)))
    print(f"wrote {path} rows={len(rows)}")
    for row in rows:
        if not row["primary"]:
            continue
        by = row["score"]["by_period"]

        def brief(period):
            block = by.get(period, {})
            return (f"{period} fires={block.get('fires')} hits={block.get('hits')} "
                    f"lift={block.get('lift')} base={block.get('base_rate')} "
                    f"starts={block.get('base_fires')}")

        boot = row["bootstrap"].get("validation", {})
        print(f"{row['asset']} {row['label']} verdict={row['verdict']} "
              f"tv={row['train_val_fires']} neighbours_hold={row['neighbours_hold']}")
        print(f"  {brief('train')} | {brief('validation')} | {brief('test')}")
        print(f"  val lo={boot.get('lo')} hi={boot.get('hi')} n={boot.get('n')} "
              f"draws={boot.get('draws')}")


if __name__ == "__main__":
    main()
