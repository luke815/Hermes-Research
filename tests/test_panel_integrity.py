"""A panel file must be sorted by date with no duplicate dates.

A descending file would make every rolling measure read the future as the
past, so the reader refuses one rather than scoring it.
"""

import pandas as pd
import pytest

from regime_tester.panel_integrity import assert_sorted, clean_frame


def test_descending_file_fails():
    frame = pd.DataFrame({"date": ["2026-11-16", "2026-11-15", "2026-11-14"], "close": [1, 2, 3]})
    with pytest.raises(AssertionError):
        assert_sorted(frame)


def test_clean_sorts_and_drops_the_future():
    frame = pd.DataFrame({
        "date": ["2026-11-16", "2026-11-16", "2026-11-18", "2026-11-15"],
        "close": [2.0, 9.0, 5.0, 1.0],
    })
    cleaned = clean_frame(frame, today="2026-11-17")
    assert list(cleaned["date"]) == ["2026-11-15", "2026-11-16"]
    assert list(cleaned["close"]) == [1.0, 2.0]
    assert_sorted(cleaned)
