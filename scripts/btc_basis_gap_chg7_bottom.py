"""btc_basis_gap_chg7_bottom, pre-registered in research/generated.md on 2026-11-16.

The factor is the 7-day change in the BTC basis minus the ETH basis, lagged
one bar by the percentile itself. The extreme is at or above its trailing
one-year 90th percentile, neighbours at the 85th and the 95th. Scored against
the amended bottom event. Reads the retained options files. Does not pull and
does not write the panel.
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
    RAW,
    clean,
    evaluate,
    event_label,
    holds,
    load_funding,
    load_ohlcv,
    train_val_episodes,
    verdict_for,
    year_caveat,
)
from regime_tester.events import rolling_percentile  # noqa: E402

SEED = 65
CHANGE = 7
PRIMARY = 0.90
NEIGHBOURS = (0.85, 0.95)
ASSETS = ("BTC", "ETH")
LABELS = (
    {"name": "bottom_30_20_7", "side": "bottom", "kind": "bottom",
     "h": 30, "x": 0.20, "y": 0.07, "primary": True},
    {"name": "bottom_60_30_10", "side": "bottom", "kind": "bottom",
     "h": 60, "x": 0.30, "y": 0.10, "primary": False},
)


def venue_basis(token: str) -> pd.Series:
    """Mean of the venue readings on a day, the same reduction the panel uses.

    The retained files are per venue, not per tenor, and a row with no venue
    reading is a gap. A later file wins on a duplicated date.
    """
    by_date: dict[pd.Timestamp, float] = {}
    for path in sorted(RAW.glob(f"basis_{token}_*.json")):
        loaded = json.loads(path.read_text())
        if not isinstance(loaded, list):
            continue
        for row in loaded:
            if not isinstance(row, dict) or "date" not in row:
                continue
            vals = [v for k, v in row.items()
                    if k != "date" and isinstance(v, (int, float))]
            if not vals:
                continue
            stamp = pd.to_datetime(int(row["date"]), unit="ms", utc=True).normalize()
            by_date[stamp] = sum(vals) / len(vals)
    return pd.Series(by_date, dtype=float).sort_index().rename(f"basis_{token}")


def basis_gap_change() -> pd.Series:
    """7-day change of the BTC basis minus the ETH basis, venue mean.

    The first 7 bars stay empty. The percentile ranks the prior bar, so bar t
    never enters its own reading.
    """
    gap = (venue_basis("btc") - venue_basis("eth")).dropna()
    return gap.diff(CHANGE).rename("basis_gap_chg7")


def lookahead_holds(close: pd.Series, gap: pd.Series) -> bool:
    """Perturb every price after day t. The label uses future prices, so the
    check is on the factor and its rank, which must not move at or before t."""
    t = len(close) // 2
    factor = basis_gap_change()
    rank = rolling_percentile(factor)
    perturbed = close.copy()
    perturbed.iloc[t + 1:] = perturbed.iloc[t + 1:] * 3
    again = basis_gap_change()
    again_rank = rolling_percentile(again)
    return bool(factor.equals(again)) and bool(rank.equals(again_rank)) and bool(
        factor.iloc[:t + 1].equals(gap.iloc[:t + 1]))


def score_asset(asset: str, close: pd.Series, rank: pd.Series,
                funding: pd.Series | None) -> tuple[list, dict]:
    rows = []
    base = {}
    for spec in LABELS:
        label = event_label(close, spec)
        base[spec["name"]] = year_caveat(label)
        scored = []
        for cut in (PRIMARY,) + NEIGHBOURS:
            row = evaluate("basis_gap_chg7", spec["side"], rank, cut, label, close,
                           funding, spec["h"], SEED)
            row["asset"] = asset
            row["label"] = spec["name"]
            row["transform"] = "change_7_percentile_1y"
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
    bars = load_ohlcv()
    funding = load_funding()
    gap = basis_gap_change()
    last_close = max(bars[asset].index.max() for asset in ASSETS)
    last_gap = gap.dropna().index.max()
    age = (pd.Timestamp(stamp, tz="UTC") - last_close).days
    print(f"today={stamp} panel_end={last_close.strftime('%Y-%m-%d')} age={age}d "
          f"basis_end={last_gap.strftime('%Y-%m-%d')} basis_n={int(gap.notna().sum())}",
          flush=True)
    if age > 2:
        sys.exit(f"stale: last close {last_close.date()} is {age} days behind {stamp}")
    missing = [asset for asset in ASSETS if asset not in bars]
    if missing:
        sys.exit(f"missing closes: {missing}")

    rank = rolling_percentile(gap)
    rows = []
    base = {}
    lookahead = {}
    for asset in ASSETS:
        asset_rows, asset_base = score_asset(
            asset, bars[asset]["c"], rank.reindex(bars[asset]["c"].index),
            funding.get(asset))
        rows.extend(asset_rows)
        base[asset] = asset_base
        lookahead[asset] = lookahead_holds(bars[asset]["c"], gap)
        print(f"{asset} rows={len(asset_rows)} lookahead={lookahead[asset]}", flush=True)
    if not all(lookahead.values()):
        sys.exit(f"lookahead failed: {lookahead}")

    out = {
        "today": stamp,
        "panel_end": last_close.strftime("%Y-%m-%d"),
        "basis_end": last_gap.strftime("%Y-%m-%d"),
        "age_days": int(age),
        "candidate": "btc_basis_gap_chg7_bottom",
        "rule": "7-day change in the venue-mean BTC basis minus the venue-mean ETH "
                "basis, lagged one bar, at or above its trailing one-year percentile",
        "primary_cut": PRIMARY,
        "neighbours": list(NEIGHBOURS),
        "label": "amended B(30, 20, 7) on candidate days; B(60, 30, 10) reported",
        "horizon_days": 30,
        "assets": list(ASSETS),
        "lookahead_holds": lookahead,
        "base_rates": base,
        "rows": rows,
    }
    path = ROOT / "results" / f"{stamp}_btc_basis_gap_chg7_bottom.json"
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
