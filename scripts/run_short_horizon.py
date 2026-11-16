"""Rescore the four live factors at 1 day and 3 days on the current panel.

Pre-registered in research/log.md on 2026-11-16 before any number was
computed. Writes results/<today>_btc_short_horizon.json. Every date comes
from the clock or the panel, never from a literal.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from regime_tester.costs import apply_costs
from regime_tester.factors import build_factors
from regime_tester.heat import COMPONENTS
from regime_tester.periods import nonoverlapping_spread, spread_by_period, spread_by_year

PANEL = Path(__file__).resolve().parent.parent / "data" / "panel.csv"
HORIZONS = (1, 3, 10)
CUTS = ((0.20, 0.80), (0.25, 0.75), (0.15, 0.85))
ASSETS = ("btc_price", "alt_price")
T_BAR = 3.0
MIN_INDEPENDENT = 40


def _pct(row: dict) -> dict:
    out = {}
    for key, value in row.items():
        if key in ("spread", "top_mean", "bot_mean") and value == value:
            out[key + "_pct"] = round(value * 100, 4)
        elif isinstance(value, float):
            out[key] = None if value != value else round(value, 4)
        else:
            out[key] = value
    return out


def _sign(row: dict) -> int:
    spread = row.get("spread")
    if spread is None or spread != spread or spread == 0:
        return 0
    return 1 if spread > 0 else -1


def main() -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    panel = pd.read_csv(PANEL, index_col=0, parse_dates=True)
    factors = build_factors(panel)

    # Lookahead check: tripling every price after the middle bar must not
    # move the factor at that bar. The forward return is not checked here;
    # it is defined to use prices after the bar.
    mid = panel.index[len(panel) // 2]
    before = {name: float(factors.loc[mid, name]) for name in COMPONENTS}
    bumped = panel.copy()
    bumped.loc[bumped.index > mid, ["btc_price", "eth_price", "alt_price"]] *= 3
    after = build_factors(bumped)
    lookahead = {
        name: before[name] == float(after.loc[mid, name]) for name in COMPONENTS
    }

    rows = []
    for factor_name in COMPONENTS:
        factor = factors[factor_name]
        for asset in ASSETS:
            funding = panel["btc_funding"] if asset == "btc_price" else panel["alt_funding"]
            for horizon in HORIZONS:
                net = apply_costs(panel[asset], horizon, 1, funding, oi_usd=None)
                for low, high in CUTS:
                    by_period = spread_by_period(factor, net["net"], horizon, low, high)
                    gross = spread_by_period(factor, net["gross"], horizon, low, high)
                    by_year = spread_by_year(factor, net["net"], horizon, low, high)
                    pooled = nonoverlapping_spread(factor, net["net"], horizon, low, high)
                    signs = {name: _sign(row) for name, row in by_period.items()}
                    rows.append({
                        "factor": factor_name,
                        "asset": asset,
                        "horizon_days": horizon,
                        "cut_low": low,
                        "cut_high": high,
                        "primary": low == 0.20 and high == 0.80,
                        "signs": signs,
                        "sign_holds_held_out": signs["validation"] != 0 and signs["validation"] == signs["test"],
                        "pooled": _pct(pooled),
                        "by_period": {name: _pct(row) for name, row in by_period.items()},
                        "gross_by_period": {name: _pct(row) for name, row in gross.items()},
                        "by_year": [_pct(row) for row in by_year],
                        "oi_missing": True,
                        "funding_missing": False,
                    })
    out = {
        "candidate": "btc_short_horizon",
        "date": today,
        "panel_path": str(PANEL),
        "panel_rows": int(len(panel)),
        "panel_start": str(panel.index.min().date()),
        "panel_end": str(panel.index.max().date()),
        "factors": list(COMPONENTS),
        "basket_note": "alt_price is the fixed 20 names chosen today, applied to the whole history; survivor-biased until the point-in-time universe exists",
        "cost_note": "net of thin-tier round trip, 0.6 percent, plus funding carry; panel has no USD open interest so every row takes the thin tier",
        "t_method": "non-overlapping, every h-th bar, unequal-variance t",
        "t_bar": T_BAR,
        "min_independent": MIN_INDEPENDENT,
        "lookahead_mid_bar": str(mid.date()),
        "lookahead_passed": all(lookahead.values()),
        "lookahead": lookahead,
        "rows": rows,
    }
    dest = Path(__file__).resolve().parent.parent / "results" / f"{today}_btc_short_horizon.json"
    dest.write_text(json.dumps(out, indent=2))
    print(f"wrote {dest}")
    print(f"today={today} panel_end={out['panel_end']} rows={out['panel_rows']} factor_rows={len(rows)}")
    print(f"lookahead_passed={out['lookahead_passed']} mid={out['lookahead_mid_bar']}")


if __name__ == "__main__":
    main()
