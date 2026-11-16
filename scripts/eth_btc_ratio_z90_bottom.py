"""eth_btc_ratio_z90_bottom, pre-registered in research/log.md on 2026-11-16.

The factor is the ETH close over the BTC close, its trailing 90-day z-score
built from bars strictly before day t. The extreme is that z-score at or
below its trailing one-year 10th percentile, neighbours at the 5th and the
15th. Scored against the amended bottom event on each asset's own close.
Reads the retained Coinalyze file. Does not pull and does not write the panel.
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
WINDOW = 90
PRIMARY = 0.10
NEIGHBOURS = (0.05, 0.15)
ASSETS = ("BTC", "ETH")
LABELS = (
    {"name": "bottom_30_20_7", "side": "bottom", "kind": "bottom",
     "h": 30, "x": 0.20, "y": 0.07, "primary": True},
    {"name": "bottom_60_30_10", "side": "bottom", "kind": "bottom",
     "h": 60, "x": 0.30, "y": 0.10, "primary": False},
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


def ratio_z90(eth: pd.Series, btc: pd.Series) -> pd.Series:
    """Trailing 90-day z-score of ETH/BTC. Bar t uses only bars before t.

    The first bars stay empty until the window has 45 prior observations.
    A zero standard deviation stays empty rather than becoming a number.
    """
    ratio = (eth / btc).replace([np.inf, -np.inf], np.nan).dropna()
    past = ratio.shift(1)
    mean = past.rolling(WINDOW, min_periods=WINDOW // 2).mean()
    std = past.rolling(WINDOW, min_periods=WINDOW // 2).std().replace(0, np.nan)
    return ((past - mean) / std).rename("eth_btc_ratio_z90")


def lookahead_holds(eth: pd.Series, btc: pd.Series) -> bool:
    """Perturb every price after day t. The factor and its rank at t must not move."""
    joined = pd.concat([eth.rename("eth"), btc.rename("btc")], axis=1).dropna()
    t = len(joined) // 2
    factor = ratio_z90(joined["eth"], joined["btc"])
    rank = rolling_percentile(factor)
    perturbed = joined.copy()
    perturbed.iloc[t + 1:, :] = perturbed.iloc[t + 1:, :] * 3
    again = ratio_z90(perturbed["eth"], perturbed["btc"])
    again_rank = rolling_percentile(again)
    stamp = joined.index[t]
    return bool(factor.loc[:stamp].equals(again.loc[:stamp])) and bool(
        rank.loc[:stamp].equals(again_rank.loc[:stamp]))


def score_asset(asset: str, close: pd.Series, factor: pd.Series,
                funding: pd.Series | None) -> tuple[list, dict]:
    rank = rolling_percentile(factor).reindex(close.index)
    rows = []
    base = {}
    for spec in LABELS:
        label = event_label(close, spec)
        base[spec["name"]] = year_caveat(label)
        scored = []
        for cut in (PRIMARY,) + NEIGHBOURS:
            row = evaluate("eth_btc_ratio_z90", spec["side"], rank, cut, label, close,
                           funding, spec["h"], SEED)
            row["asset"] = asset
            row["label"] = spec["name"]
            row["transform"] = "zscore_90_percentile_1y"
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
    missing = [asset for asset in ASSETS if asset not in closes]
    if missing:
        sys.exit(f"missing closes: {missing}")
    last = max(series.index.max() for series in closes.values())
    age = (pd.Timestamp(stamp, tz="UTC") - last).days
    print(f"today={stamp} panel_end={last.strftime('%Y-%m-%d')} age={age}d", flush=True)
    if age > 2:
        sys.exit(f"stale: last close {last.date()} is {age} days behind {stamp}")

    factor = ratio_z90(closes["ETH"], closes["BTC"])
    if not lookahead_holds(closes["ETH"], closes["BTC"]):
        sys.exit("lookahead failed")
    print(f"factor_end={factor.dropna().index.max().strftime('%Y-%m-%d')} "
          f"n={int(factor.notna().sum())} lookahead=True", flush=True)

    rows = []
    base = {}
    for asset in ASSETS:
        asset_rows, asset_base = score_asset(
            asset, closes[asset], factor, funding.get(asset))
        rows.extend(asset_rows)
        base[asset] = asset_base
        print(f"{asset} rows={len(asset_rows)}", flush=True)

    out = {
        "today": stamp,
        "panel_end": last.strftime("%Y-%m-%d"),
        "age_days": int(age),
        "candidate": "eth_btc_ratio_z90_bottom",
        "extends": "eth_btc_30d_conditioning, insufficient 2026-11-16, by changing the transform and the target",
        "rule": "ETH/BTC trailing 90-day z-score from bars before t, at or below its trailing one-year percentile",
        "primary_cut": PRIMARY,
        "neighbours": list(NEIGHBOURS),
        "label": "amended B(30, 20, 7) on candidate days; B(60, 30, 10) reported",
        "horizon_days": 30,
        "assets": list(ASSETS),
        "lookahead_holds": {"BTC": True, "ETH": True},
        "factor_observations": int(factor.notna().sum()),
        "base_rates": base,
        "rows": rows,
    }
    path = ROOT / "results" / f"{stamp}_eth_btc_ratio_z90_bottom.json"
    path.write_text(json.dumps(clean(out)))
    print(f"wrote {path} rows={len(rows)}")
    for row in rows:
        if not row["primary"]:
            continue
        by = row["score"]["by_period"]

        def brief(period):
            block = by.get(period, {})
            return (f"{period} fires={block.get('fires')} hits={block.get('hits')} "
                    f"lift={block.get('lift')}")

        boot = row["bootstrap"].get("validation", {})
        print(f"{row['asset']} {row['label']} verdict={row['verdict']} "
              f"neighbours_hold={row['neighbours_hold']} "
              f"train_val_fires={row['train_val_fires']}")
        print(f"  {brief('train')} | {brief('validation')} | {brief('test')}")
        print(f"  val lo={boot.get('lo')} hi={boot.get('hi')} n={boot.get('n')} draws={boot.get('draws')}")


if __name__ == "__main__":
    main()
