"""A panel file must be sorted by date with no duplicate dates.

A descending file would make every rolling measure read the future as the past.
"""

import pandas as pd


def assert_sorted(frame):
    dates = frame["date"]
    assert dates.is_monotonic_increasing, "dates are not sorted"
    assert dates.duplicated().sum() == 0, "duplicate dates"


def test_descending_file_fails():
    frame = pd.DataFrame({"date": ["2026-11-16", "2026-11-15", "2026-11-14"], "close": [1, 2, 3]})
    try:
        assert_sorted(frame)
    except AssertionError:
        return
    raise AssertionError("a descending file was accepted")
