"""D22 counts one episode per overlapping window, not one per name.

Two names whose bottom episodes start within the horizon of each other are
the same move. Counting each name's start would report the same window many
times, and the pooled count is what the pass bar is applied to.
"""

import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scripts.score_d22 as score  # noqa: E402


class PooledEpisodes(unittest.TestCase):
    def test_two_names_inside_one_window_count_as_one_episode(self):
        first = pd.Timestamp("2024-01-01", tz="UTC")
        second = first + pd.Timedelta(days=score.HORIZON)
        third = first + pd.Timedelta(days=score.HORIZON + 1)
        self.assertEqual(len(score.cluster([first, second], score.HORIZON)), 1)
        self.assertEqual(len(score.cluster([first, third], score.HORIZON)), 2)

    def test_a_fire_on_one_name_catches_the_shared_window(self):
        index = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")
        rank = pd.Series([0.5, 0.05, 0.5, 0.5, 0.5], index=index)
        starts = pd.DatetimeIndex([index[1]])
        other_rank = pd.Series([0.5], index=pd.DatetimeIndex([index[2]]))
        other_starts = pd.DatetimeIndex([index[2]])
        scored = score.score_cut(
            [(rank.reindex(starts), starts), (other_rank, other_starts)], 0.10)
        self.assertEqual(scored["train"]["episodes"], 1)
        self.assertEqual(scored["train"]["fires"], 1)


if __name__ == "__main__":
    unittest.main()
