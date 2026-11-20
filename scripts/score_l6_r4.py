"""R3: the exposure harness, and R4: the dial variants against buy and hold.

The dial is exposure times the next day's return, net of the costs table
on every change in exposure. Funding carry is not on this panel, so a day
with no carry is dropped rather than treated as zero, and the result says
so. The periods are the fixed three. Admission needs the full dial to beat
buy and hold on maximum drawdown and Calmar in validation and in test, and
to beat the 200-day rule on Calmar in both. This script writes both files.
It does not pull.
"""

import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from regime_tester.costs import TAKER_FEE_PER_SIDE, SLIPPAGE_LIQUID_PER_SIDE  # noqa: E402
from regime_tester.derivatives import market_measures  # noqa: E402
from regime_tester.periods import assign_period  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402
from regime_tester.risk import readings, run_states  # noqa: E402

PANEL = os.path.join(ROOT, "data", "panel.csv")
COST_PER_UNIT = (TAKER_FEE_PER_SIDE + SLIPPAGE_LIQUID_PER_SIDE) * 2


def _max_drawdown(returns):
    equity = (1 + returns.fillna(0)).cumprod()
    peak = equity.cummax()
    return float((equity / peak - 1).min()) if len(equity) else None


def _cagr(returns):
    if len(returns) < 2:
        return None
    equity = float((1 + returns.fillna(0)).prod())
    years = len(returns) / 365
    if years <= 0 or equity <= 0:
        return None
    return float(equity ** (1 / years) - 1)


def _calmar(returns):
    cagr = _cagr(returns)
    drawdown = _max_drawdown(returns)
    if cagr is None or not drawdown:
        return None
    return float(cagr / abs(drawdown))


def _metrics(returns):
    return {
        "days": int(returns.notna().sum()),
        "cagr": _cagr(returns),
        "max_drawdown": _max_drawdown(returns),
        "calmar": _calmar(returns),
    }


def _by_period(returns):
    period = assign_period(returns.index)
    out = {}
    for name in ("train", "validation", "test"):
        mask = period.eq(name)
        out[name] = _metrics(returns[mask])
    return out


def _by_year(returns):
    out = {}
    for year, block in returns.groupby(returns.index.year):
        out[str(int(year))] = _metrics(block)
    return out


def variants(close, walked):
    """The dial, the 200-day rule, and buy and hold, on the same dates."""
    forward = close.shift(-1) / close - 1
    change = walked["dial"].diff().abs().fillna(walked["dial"])
    dial_net = walked["dial"] * forward - change * COST_PER_UNIT
    above = walked["btc_vs_200d"].ge(0).astype(float)
    rule_change = above.diff().abs().fillna(above)
    rule_net = above * forward - rule_change * COST_PER_UNIT
    hold = forward.copy()
    return {
        "full_dial": dial_net,
        "trend_200d": rule_net,
        "buy_and_hold": hold,
    }


def score():
    panel = pd.read_csv(PANEL, index_col=0, parse_dates=True)
    panel.index = pd.to_datetime(panel.index, utc=True)
    market = market_measures()
    walked = run_states(readings(panel, market))
    close = panel["btc_price"].astype(float).reindex(walked.index)
    built = variants(close, walked)
    table = {}
    for name, series in built.items():
        table[name] = {"by_period": _by_period(series), "by_year": _by_year(series)}
    dial = table["full_dial"]["by_period"]
    hold = table["buy_and_hold"]["by_period"]
    rule = table["trend_200d"]["by_period"]
    beats = {}
    for period in ("validation", "test"):
        dial_dd = dial[period]["max_drawdown"]
        hold_dd = hold[period]["max_drawdown"]
        beats[period] = {
            "drawdown_vs_hold": None if None in (dial_dd, hold_dd) else bool(dial_dd > hold_dd),
            "calmar_vs_hold": _beats(dial[period]["calmar"], hold[period]["calmar"]),
            "calmar_vs_200d": _beats(dial[period]["calmar"], rule[period]["calmar"]),
        }
    admitted = all(
        beats[period]["drawdown_vs_hold"] and beats[period]["calmar_vs_hold"]
        and beats[period]["calmar_vs_200d"]
        for period in ("validation", "test"))
    return {
        "panel_rows": int(len(panel)),
        "as_of": str(walked.index[-1].date()),
        "cost_per_unit_change": COST_PER_UNIT,
        "carry": "dropped: the panel has no funding column, so carry is not treated as zero",
        "variants": table,
        "beats": beats,
        "state_changes": int((walked["state"] != walked["state"].shift(1)).sum()),
        "verdict": "admitted" if admitted else "rejected",
        "reason": ("the full dial beats buy and hold on drawdown and Calmar, and the "
                   "200-day rule on Calmar, in validation and in test"
                   if admitted else
                   "the full dial does not beat both benchmarks in both held-out periods"),
    }


def _beats(left, right):
    if left is None or right is None:
        return None
    return bool(left > right)


def main():
    payload = score()
    r3 = {
        "item": "R3",
        "as_of": payload["as_of"],
        "panel_rows": payload["panel_rows"],
        "cost_per_unit_change": payload["cost_per_unit_change"],
        "carry": payload["carry"],
        "variants": list(payload["variants"]),
        "verdict": "recorded",
        "reason": "the harness runs the dial as exposure times the next day's return, net of costs on changes",
    }
    path = write_result("l6_r3", r3, inputs=["data/panel.csv", "data/laevitas/market"])
    print(path)
    r4 = {"item": "R4", **payload}
    path = write_result("l6_r4", r4, inputs=["data/panel.csv", "data/laevitas/market"])
    print(path, r4["verdict"])


if __name__ == "__main__":
    main()
