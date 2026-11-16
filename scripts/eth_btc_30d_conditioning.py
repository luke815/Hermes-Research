"""eth_btc_30d_conditioning: the btc_ret_30 quintile spread inside terciles of
the ETH/BTC trailing 30-day return.

Pre-registered in research/generated.md (2026-11-05) and queued in
research/backlog.md before this file was run. The spread must keep its sign in
validation and test inside at least one tercile, and that tercile's spread must
exceed the unsplit spread in both. Expected n is about 20 per tercile per
period, so every cell is reported and none is quoted as an edge.

Nothing here chooses a threshold, a horizon or a period. All three are fixed
by the pre-registration.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from regime_tester.costs import apply_costs
from regime_tester.periods import assign_period, quintile_edges

PANEL = Path(__file__).resolve().parent.parent / "data" / "panel.csv"
HORIZON = 10
LOOKBACK = 30
ASSETS = ("btc_price", "alt_price")
TERCILE_MIN = 60  # expanding history before a tercile edge exists


def edges(series: pd.Series, low: float, high: float, min_history: int) -> pd.DataFrame:
    """Expanding cut-offs from values strictly before the bar."""
    past = series.shift(1).expanding(min_periods=min_history)
    return pd.DataFrame({"lo": past.quantile(low), "hi": past.quantile(high)})


def spread(part: pd.DataFrame) -> dict:
    top = part.loc[part["s"] > part["hi"], "f"]
    bot = part.loc[part["s"] < part["lo"], "f"]
    n = int(min(len(top), len(bot)))
    if len(top) < 2 or len(bot) < 2:
        return {"spread_pct": None, "t": None, "n_top": int(len(top)),
                "n_bot": int(len(bot)), "n": n,
                "thin": True, "sign": None}
    gap = float(top.mean() - bot.mean())
    se = np.sqrt(top.var(ddof=1) / len(top) + bot.var(ddof=1) / len(bot))
    t = float(gap / se) if se and not np.isnan(se) else None
    return {"spread_pct": round(gap * 100, 4),
            "t": None if t is None else round(t, 4),
            "n_top": int(len(top)), "n_bot": int(len(bot)), "n": n,
            "thin": n < 30,
            "sign": int(np.sign(gap)) if gap != 0 else 0}


def by_year(frame: pd.DataFrame) -> list[dict]:
    rows = []
    if frame.empty:
        return rows
    for year in sorted(frame.index.year.unique()):
        row = spread(frame[frame.index.year == year])
        row["year"] = int(year)
        rows.append(row)
    return rows


def main() -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    panel = pd.read_csv(PANEL, index_col=0, parse_dates=True)

    # The factor is the 30-day return as of yesterday, so bar t never uses bar t.
    factor = panel["btc_price"].pct_change(LOOKBACK).shift(1)
    # The conditioner is the ETH/BTC ratio's own 30-day return, also as of yesterday.
    ratio = panel["eth_price"] / panel["btc_price"]
    conditioner = ratio.pct_change(LOOKBACK).shift(1)
    tercile = edges(conditioner, 1 / 3, 2 / 3, TERCILE_MIN).rename(
        columns={"lo": "t_lo", "hi": "t_hi"})

    # Correlation of the conditioner with the factor it splits, on the same bars.
    corr = round(float(conditioner.corr(factor)), 4)

    periods = assign_period(panel.index)
    per_asset = {}
    for asset in ASSETS:
        funding = panel["btc_funding"] if asset == "btc_price" else panel["alt_funding"]
        net = apply_costs(panel[asset], HORIZON, 1, funding, oi_usd=None)
        q = quintile_edges(factor)
        frame = pd.concat(
            [factor.rename("s"), net["net"].rename("f"), q, tercile,
             conditioner.rename("c"), periods.rename("period")], axis=1
        ).dropna(subset=["s", "f", "lo", "hi", "t_lo", "t_hi"])
        # every h-th bar, so the 10-day windows do not share days
        stride = frame.iloc[::HORIZON]

        def band(part: pd.DataFrame) -> pd.Series:
            return pd.Series(
                np.where(part["c"] < part["t_lo"], "low",
                         np.where(part["c"] > part["t_hi"], "high", "mid")),
                index=part.index)

        stride = stride.copy()
        stride["tercile"] = band(stride)

        unsplit = {name: spread(stride[stride["period"] == name])
                   for name in ("train", "validation", "test")}
        unsplit["all"] = spread(stride)

        terciles = {}
        for label in ("low", "mid", "high"):
            cell = stride[stride["tercile"] == label]
            by_period = {name: spread(cell[cell["period"] == name])
                         for name in ("train", "validation", "test")}
            by_period["all"] = spread(cell)
            widened = {}
            for name in ("train", "validation", "test"):
                before = unsplit[name]["spread_pct"]
                after = by_period[name]["spread_pct"]
                widened[name] = (None if before is None or after is None
                                 else round(after - before, 4))
            terciles[label] = {
                "by_period": by_period,
                "widened_vs_unsplit_pct": widened,
                "by_year": by_year(cell),
                "independent_n": int(len(cell)),
            }
        per_asset[asset] = {
            "unsplit": unsplit,
            "terciles": terciles,
            "independent_n": int(len(stride)),
            "unsplit_by_year": by_year(stride),
        }

    out = {
        "job": "regime-research",
        "candidate": "eth_btc_30d_conditioning",
        "date": today,
        "written_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "panel_rows": int(len(panel)),
        "panel_end": str(panel.index.max().date()),
        "factor": "btc 30-day return, lagged one bar",
        "conditioner": "ETH/BTC ratio 30-day return, lagged one bar",
        "correlation_factor_conditioner": corr,
        "horizon_days": HORIZON,
        "stride": "every 10th usable bar, non-overlapping",
        "quintile_edges": "expanding past, shifted one bar, 20/80",
        "tercile_edges": "expanding past of the conditioner, shifted one bar, 33/67",
        "periods": "train to 2024-06-30, validation 2024-07-01 to 2025-12-31, test 2026-01-01 on",
        "note": ("net of thin-tier costs, oi_usd missing so every row takes the thin tier; "
                 "alt basket is the fixed 20 and survivor-biased; expected n about 20 per "
                 "cell so every cell is reported and none is quoted as an edge"),
        "assets": per_asset,
    }
    dest = Path(__file__).resolve().parent.parent / "results" / f"{today}_eth_btc_30d_conditioning.json"
    dest.write_text(json.dumps(out, indent=1))
    print(f"wrote {dest}")
    print(f"today={today} panel_end={out['panel_end']} rows={out['panel_rows']} corr={corr}")
    for asset, block in per_asset.items():
        print(f"--- {asset} independent_n={block['independent_n']}")
        print("  unsplit", json.dumps(block["unsplit"]))
        for label, cell in block["terciles"].items():
            print(f"  {label} n={cell['independent_n']}", json.dumps(cell["by_period"]))


if __name__ == "__main__":
    main()
