"""A cross-sectional confirmation scores the cell it is given.

Two cells with different measures must not share a validation statistic, which
is what happened when every cell was scored as 14-day momentum. A rel_ target
is refused, because it is the same test as its ret_ twin. The deflated bar
counts validation attempts in the family, and that count only rises.
"""

import numpy as np
import pandas as pd

from regime_tester.confirm import (
    _score_cross_section, family_attempts, family_of, hac_t, parse_cell_id,
)


def _panel():
    rng = np.random.default_rng(7)
    dates = pd.date_range("2024-01-01", periods=420, freq="D", tz="UTC")
    panel = {}
    for i in range(24):
        close = 100 * np.exp(np.cumsum(rng.normal(0.0004, 0.02, len(dates))))
        panel[f"n{i}"] = pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "close": close})
    return panel


def _cell(measure, target="ret_1"):
    return parse_cell_id(
        f"{measure}|raw|above|80|{target}|pit_cross_section|none|daily")


def test_two_cells_differ():
    panel = _panel()
    first = _score_cross_section(_cell("roc_12"), panel)
    second = _score_cross_section(_cell("mayer_multiple"), panel)
    assert first["validation"]["t_newey_west"] != second["validation"]["t_newey_west"]
    assert first["validation"]["spread_independent"] != second["validation"]["spread_independent"]


def test_horizon_changes_the_statistic_and_the_label():
    panel = _panel()
    one = _score_cross_section(_cell("roc_12", "ret_1"), panel)
    three = _score_cross_section(_cell("roc_12", "ret_3"), panel)
    assert "t_newey_west" in one["validation"]
    assert "t_newey_west" not in three["validation"]
    assert "hac_t" in three["validation"]
    assert three["horizon"] == 3


def test_rel_target_is_refused():
    try:
        parse_cell_id("roc_12|raw|above|80|rel_1|pit_cross_section|none|daily")
    except ValueError:
        return
    raise AssertionError("a rel_ cross-sectional target was accepted")


def test_family_count_only_rises():
    rows = [
        {"cell_id": "roc_12|raw|above|80|ret_1|btc|none|daily", "validation": {"n": 1}},
        {"cell_id": "roc_12|raw|above|90|ret_1|btc|none|daily", "validation": {"n": 1}},
        {"cell_id": "sma_20|raw|above|80|ret_1|btc|none|daily", "validation": None},
    ]
    counts = family_attempts(rows)
    assert family_of(rows[0]["cell_id"]) == "momentum"
    assert counts["momentum"] == 2
    assert "trend" not in counts
    counts["momentum"] += 1
    assert family_attempts(rows)["momentum"] == 2


def test_overlapping_t_is_not_labelled_newey_west():
    values = np.arange(12, dtype=float)
    assert set(hac_t(values, 1)) == {"t_newey_west"}
    assert set(hac_t(values, 10)) == {"hac_t"}
    assert hac_t(values, 10)["hac_t"] != hac_t(values, 1)["t_newey_west"]
