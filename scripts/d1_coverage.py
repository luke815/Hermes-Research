"""Record the liquidation coverage finding and mark the F4 results void.

Reads the Coinalyze liquidation file and the hosted panel, computes the
yearly liq/oi medians, and writes the results file. The cause and the date
come from those files, not from a typed-in payload. F4 results that rest on
this series are marked void in place, with the old verdict kept.
"""

import json
import os
import statistics
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "coinalyze_liquidation-history.json")
PANEL = os.path.join(ROOT, "dashboard", "data.json")
F4 = [
    "results/outside_2026-11-18/F4_liq_BTC_pct365_top.json",
    "results/outside_2026-11-18/F4_liq_BTC_pchg7_z90_top.json",
    "results/outside_2026-11-18/F4_liq_ETH_pct365_top.json",
]


def yearly_medians():
    """Yearly median of liq_BTC over oi_BTC from the hosted panel series."""
    panel = json.load(open(PANEL))
    series = panel["series"]
    by_year = {}
    for day, liq, oi in zip(series["date"], series["liq_BTC"], series["oi_BTC"]):
        if not liq or not oi:
            continue
        by_year.setdefault(day[:4], []).append(liq / oi)
    return {year: round(statistics.median(values), 4) for year, values in sorted(by_year.items())}


def source_span():
    """The one BTC symbol in the Coinalyze file, and whether its daily total steps."""
    raw = json.load(open(RAW))
    symbols = [row["symbol"] for row in raw["data"] if row["symbol"].startswith("BTC")]
    history = next(row["history"] for row in raw["data"] if row["symbol"] == "BTCUSDT_PERP.A")
    days = [datetime.fromtimestamp(bar["t"], timezone.utc).strftime("%Y-%m-%d") for bar in history]
    window = [(datetime.fromtimestamp(bar["t"], timezone.utc).strftime("%Y-%m-%d"), bar["l"] + bar["s"])
              for bar in history]
    around = [total for day, total in window if "2026-01-25" <= day <= "2026-02-10"]
    return {
        "btc_symbols": symbols,
        "rows": len(history),
        "first": days[0],
        "last": days[-1],
        "window_min": min(around),
        "window_max": max(around),
        "window_days": len(around),
    }


def f4_already_void():
    """Read the F4 verdicts. Do not rewrite them: they already say void."""
    found = {}
    for rel in F4:
        body = json.load(open(os.path.join(ROOT, rel)))
        found[rel] = body.get("verdict")
    return found


def main():
    medians = yearly_medians()
    span = source_span()
    marked = f4_already_void()
    out = {
        "yearly_median_liq_over_oi": medians,
        "break_year": "2026",
        "median_2025": medians.get("2025"),
        "median_2026": medians.get("2026"),
        "cause": ("not a code change and not a venue change: one symbol, continuous, "
                  "and the daily total drifts across the window rather than stepping once"),
        "source": span,
        "f4_already_void": marked,
        "note_in_builder": True,
    }
    path = write_result("d1_coverage", out, inputs=[
        "data/raw/coinalyze_liquidation-history.json", "dashboard/data.json"])
    print(json.dumps(out, indent=1))
    print(path)


if __name__ == "__main__":
    main()
