"""The weekly close keeps a week only when its Sunday is in the panel."""

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from score_c10 import weekly_close  # noqa: E402


class WeeklyClose(unittest.TestCase):
    def test_a_week_without_its_sunday_is_dropped(self):
        index = pd.to_datetime(
            ["2024-01-01", "2024-01-07", "2024-01-08", "2024-01-13"], utc=True)
        daily = pd.Series([1.0, 2.0, 3.0, 4.0], index=index)
        weekly = weekly_close(daily)
        self.assertEqual(list(weekly), [2.0])
        self.assertEqual(str(weekly.index[0])[:10], "2024-01-07")


if __name__ == "__main__":
    unittest.main()
