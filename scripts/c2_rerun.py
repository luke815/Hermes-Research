"""C2 rerun on the amended labels.

Pre-registered in research/log.md on 2026-11-15 before this script existed.
The factors, the cuts and the lag are the ones fixed on 2026-11-02. The
labels are the amended ones. Reads the retained Coinalyze files and the
Laevitas basis files already on disk. Does not pull and does not write the
panel.
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
RAW = ROOT / "data" / "raw"

from regime_tester.cycle_score import (  # noqa: E402
    HORIZON,
    LABELS,
    NEIGHBOURS,
    PRIMARY,
    clean,
    evaluate,
    event_label,
    holds,
    train_val_episodes,
    verdict_for,
    year_caveat,
)
from regime_tester.events import (  # noqa: E402
    STREAK_DAYS,
    STREAK_HIGH,
    STREAK_LOW,
    STREAK_NEIGHBOURS,
    rolling_percentile,
    streak,
)
def load_series(name, fields):
    """One frame per asset from a retained Coinalyze file. No pull."""
    blob = json.loads((RAW / name).read_text())
    names = {symbol: asset for asset, symbol in blob["symbols"].items()}
    out = {}
    for entry in blob["data"]:
        if entry["symbol"] not in names:
            continue
        frame = pd.DataFrame(entry["history"])
        index = pd.to_datetime(frame["t"], unit="s", utc=True).dt.normalize()
        taken = frame.loc[:, list(fields)].apply(pd.to_numeric, errors="coerce")
        taken.index = index
        out[names[entry["symbol"]]] = taken[~taken.index.duplicated(keep="last")].sort_index()
    return out


def load_basis_series(token):
    rows = []
    for path in sorted(RAW.glob(f"basis_{token.lower()}*.json")):
        rows.extend(json.loads(path.read_text()))
    by_date = {}
    for row in rows:
        venues = [v for k, v in row.items() if k != "date" and isinstance(v, (int, float))]
        if not venues or "date" not in row:
            continue
        stamp = pd.to_datetime(row["date"], unit="ms", utc=True).normalize()
        by_date.setdefault(stamp, []).extend(venues)
    series = pd.Series({stamp: float(np.mean(values)) for stamp, values in by_date.items()})
    return series.sort_index().rename(f"basis_{token.lower()}")

SEED = 62
MIN_VETO = 15


def extreme_flag(rank, side, cut):
    if side == "top":
        return rank.ge(cut)
    return rank.le(cut)


def build_factors(frames, basis):
    """The positioning family retained history can actually build.

    Open interest and liquidations start in 2022-09, so their train window
    is short and the result says so.
    """
    out = {}
    notes = {}
    if "funding" in frames:
        funding = frames["funding"]["c"]
        out["funding_7d"] = funding.rolling(7, min_periods=7).mean()
        out["funding_streak_high"] = funding
        out["funding_streak_low"] = funding
    if "oi" in frames and "volume" in frames:
        oi = frames["oi"]["c"]
        volume = frames["volume"]["v"]
        out["oi_vs_90d_high"] = oi / oi.rolling(90, min_periods=90).max()
        out["oi_change_30d"] = oi.pct_change(30)
        out["oi_over_volume"] = oi / volume.rolling(30, min_periods=30).mean()
        notes["oi"] = "open interest and liquidations start in 2022-09, so train is short"
    if "liq" in frames and "oi" in frames:
        oi = frames["oi"]["c"]
        out["long_liq_3d"] = frames["liq"]["l"].rolling(3, min_periods=3).sum() / oi
        out["short_liq_3d"] = frames["liq"]["s"].rolling(3, min_periods=3).sum() / oi
    if "lsr" in frames:
        out["lsr"] = frames["lsr"]["r"]
    if basis is not None:
        out["basis"] = basis.reindex(frames["close"].index)
    return out, notes


def one_cell(name, side, rank, cut, label, close, funding, horizon, primary):
    row = evaluate(name, side, rank, cut, label, close, funding, horizon, SEED)
    row["transform"] = "percentile_1y"
    row["primary"] = primary
    return row


def score_asset(asset, frames, basis, funding):
    """Every factor against every label, primary cut and both neighbours."""
    factors, notes = build_factors(frames, basis)
    close = frames["close"]
    rows = []
    base = {}
    for spec in LABELS:
        label = event_label(close, spec)
        base[spec["name"]] = year_caveat(label)
        side = spec["side"]
        for name, series in factors.items():
            aligned = series.reindex(close.index)
            rank = rolling_percentile(aligned)
            if name.startswith("funding_streak"):
                side_name = "top" if name.endswith("high") else "bottom"
                if side_name != side:
                    continue
                flag = extreme_flag(rank, side_name, STREAK_HIGH if side_name == "top" else STREAK_LOW)
                for days in (STREAK_DAYS,) + STREAK_NEIGHBOURS:
                    lit = streak(flag.fillna(False), days).where(rank.notna(), False).astype(float)
                    row = evaluate(f"{name}_{days}d", side, lit, 0.5, label, close,
                                   funding, spec["h"], SEED)
                    row["asset"] = asset
                    row["label"] = spec["name"]
                    row["transform"] = "streak"
                    row["primary"] = days == STREAK_DAYS
                    row["note"] = "cut 0.5 is the streak flag, not a percentile"
                    row["neighbours_hold"] = None
                    row["verdict"] = verdict_for(row, True) if days == STREAK_DAYS else "neighbour"
                    rows.append(row)
                continue
            cuts = (PRIMARY[side],) + NEIGHBOURS[side]
            scored = []
            for cut in cuts:
                row = one_cell(name, side, rank, cut, label, close, funding, spec["h"],
                               cut == PRIMARY[side])
                row["asset"] = asset
                row["label"] = spec["name"]
                if name.startswith("oi_") or name.endswith("_liq_3d"):
                    row["note"] = notes.get("oi", "")
                scored.append(row)
            primary = scored[0]
            neighbours = scored[1:]
            primary["neighbours_hold"] = holds(primary, neighbours) if spec["primary"] else None
            primary["verdict"] = verdict_for(primary, bool(primary["neighbours_hold"])) if spec["primary"] else "reported"
            rows.append(primary)
            for other in neighbours:
                other["verdict"] = "neighbour"
                rows.append(other)
    return rows, base


def pool_episodes(rows_by_asset):
    """One episode per overlapping window across names, not one per name.

    Two names whose episode starts fall within the horizon of each other
    are the same move. The pooled count is the number of such clusters.
    """
    starts = []
    for asset, frame in rows_by_asset.items():
        for stamp in frame:
            starts.append((stamp, asset))
    starts.sort()
    clusters = 0
    last = None
    for stamp, _asset in starts:
        if last is None or (stamp - last).days > HORIZON:
            clusters += 1
        last = stamp
    return clusters


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    closes = load_series("coinalyze_ohlcv-history.json", ("c", "v"))
    funding = load_series("coinalyze_funding-rate-history.json", ("c",))
    oi = load_series("coinalyze_open-interest-history.json", ("c",))
    liq = load_series("coinalyze_liquidation-history.json", ("l", "s"))
    lsr = load_series("coinalyze_long-short-ratio-history.json", ("r",))
    basis = {"BTC": load_basis_series("btc"), "ETH": load_basis_series("eth")}
    last = max(frame.index.max() for frame in closes.values())
    age = (pd.Timestamp(stamp, tz="UTC") - last).days
    print(f"today={stamp} panel_end={last.strftime('%Y-%m-%d')} age={age}d", flush=True)
    if age > 2:
        sys.exit(f"stale: last close {last.date()} is {age} days behind {stamp}")

    assets = sorted(closes)
    rows = []
    base = {}
    for asset in assets:
        frames = {"close": closes[asset]["c"], "volume": closes[asset]}
        if asset in funding:
            frames["funding"] = funding[asset]
        if asset in oi:
            frames["oi"] = oi[asset]
        if asset in liq:
            frames["liq"] = liq[asset]
        if asset in lsr:
            frames["lsr"] = lsr[asset]
        asset_rows, asset_base = score_asset(
            asset, frames, basis.get(asset), funding[asset]["c"] if asset in funding else None)
        rows.extend(asset_rows)
        base[asset] = asset_base
        print(f"{asset} rows={len(asset_rows)}", flush=True)

    out = {
        "today": stamp,
        "panel_end": last.strftime("%Y-%m-%d"),
        "age_days": int(age),
        "candidate": "c2_rerun",
        "label": "amended T(30, 20) and B(30, 20, 7) on candidate days, neighbours reported",
        "horizon_days": HORIZON,
        "assets": assets,
        "asset_count": len(assets),
        "not_tested": [
            "cross-venue funding dispersion: one venue per name in the retained file",
            "days since the last liquidation cascade: no cascade definition was pre-registered",
        ],
        "base_rates": base,
        "rows": rows,
    }
    path = ROOT / "results" / f"{stamp}_c2_rerun.json"
    path.write_text(json.dumps(clean(out)))
    print(f"wrote {path} rows={len(rows)}")


if __name__ == "__main__":
    main()
