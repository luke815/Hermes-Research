"""The cross-sectional scorer does not look ahead, and its counts add up."""

import numpy as np
import pandas as pd

from regime_tester.cross_section import event_lift, lookahead_holds, score_cross_section


def _panel(seed=0, names=30, days=120):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2023-01-01", periods=days, freq="D").strftime("%Y-%m-%d")
    out = {}
    for i in range(names):
        close = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, days)))
        out[f"n{i}"] = pd.DataFrame({"date": dates, "close": close})
    return out


def test_lookahead():
    panel = _panel()
    close = panel["n0"].set_index("date")["close"]
    assert lookahead_holds(close, lambda s: s.pct_change(10))


def test_score_covers_the_dates():
    scored = score_cross_section(_panel(), lambda s: s.pct_change(10), horizon=5)
    assert len(scored) > 90
    assert scored["rank_ic"].notna().sum() > 90


def test_event_lift_counts():
    index = pd.RangeIndex(16)
    candidates = pd.Series([True, False, True] + [False] * 13, index=index)
    events = pd.Series([False, True] + [False] * 14, index=index)
    got = event_lift(candidates, events, horizon=3)
    assert got["candidates"] == 2
    assert got["false_alarms"] == 1
    assert got["mean_lead_days"] == 1.0
