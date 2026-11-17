"""btc_funding_level_pct_bottom, pre-registered in research/generated.md.

The factor is the BTC funding close, lagged one bar by the percentile, extreme
at or below its trailing one-year 10th percentile, neighbours at the 5th and
the 15th. Scored against the amended bottom event. Reads the retained
Coinalyze files. Does not pull and does not write the panel.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

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


def lookahead_holds(funding: pd.Series) -> bool:
    """Perturb every funding value after day t. The rank at t must not move."""
    t = len(funding) // 2
    rank = rolling_percentile(funding)
    perturbed = funding.copy()
    perturbed.iloc[t + 1:] = perturbed.iloc[t + 1:] + 1
    again = rolling_percentile(perturbed)
    return bool(rank.iloc[:t + 1].equals(again.iloc[:t + 1]))


def score_asset(asset: str, close: pd.Series, funding: pd.Series) -> tuple[list, dict]:
    rank = rolling_percentile(funding).reindex(close.index)
    rows = []
    base = {}
    for spec in LABELS:
        label = event_label(close, spec)
        base[spec["name"]] = year_caveat(label)
        scored = []
        for cut in (PRIMARY,) + NEIGHBOURS:
            row = evaluate("funding_level", spec["side"], rank, cut, label, close,
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
    missing = [asset for asset in ASSETS if asset not in closes or asset not in funding]
    if missing:
        sys.exit(f"missing series: {missing}")

    rows = []
    base = {}
    lookahead = {}
    spans = {}
    for asset in ASSETS:
        asset_rows, asset_base = score_asset(asset, closes[asset], funding[asset])
        rows.extend(asset_rows)
        base[asset] = asset_base
        lookahead[asset] = lookahead_holds(funding[asset])
        spans[asset] = {
            "first": funding[asset].index.min().strftime("%Y-%m-%d"),
            "last": funding[asset].index.max().strftime("%Y-%m-%d"),
            "rows": int(funding[asset].notna().sum()),
        }
        print(f"{asset} rows={len(asset_rows)} lookahead={lookahead[asset]}", flush=True)
    if not all(lookahead.values()):
        sys.exit(f"lookahead failed: {lookahead}")

    out = {
        "today": stamp,
        "panel_end": last.strftime("%Y-%m-%d"),
        "age_days": int(age),
        "candidate": "btc_funding_level_pct_bottom",
        "rule": "funding close, lagged one bar by the percentile, at or below "
                "its trailing one-year percentile",
        "primary_cut": PRIMARY,
        "neighbours": list(NEIGHBOURS),
        "label": "amended B(30, 20, 7) on candidate days; B(60, 30, 10) reported",
        "horizon_days": 30,
        "assets": list(ASSETS),
        "funding_span": spans,
        "lookahead_holds": lookahead,
        "base_rates": base,
        "rows": rows,
    }
    path = ROOT / "results" / f"{stamp}_btc_funding_level_pct_bottom.json"
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
        print(f"  val lo={boot.get('lo')} hi={boot.get('hi')} n={boot.get('n')}")


if __name__ == "__main__":
    main()
