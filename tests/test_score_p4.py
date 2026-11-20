"""The PREREG4 scorer reads the committed rule and does not leak.

A feature at bar t that moves when a later price changes has read the future.
The flag that selects the days is a feature. The forward return is the target,
so it may move.
"""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import score_p4  # noqa: E402


class NoLeak(unittest.TestCase):
    def test_trailing_percentile_ignores_the_future(self):
        series = pd.Series(np.arange(400, dtype=float))
        before = score_p4.trailing_percentile(series, 365, 180)
        series.iloc[-1] = 10_000
        after = score_p4.trailing_percentile(series, 365, 180)
        pd.testing.assert_series_equal(before.iloc[:-1], after.iloc[:-1])

    def test_flag_does_not_move_when_a_later_price_changes(self):
        index = pd.date_range("2021-01-01", periods=500, freq="D").strftime("%Y-%m-%d")
        frame = pd.DataFrame({
            "price": np.linspace(100, 200, 500),
            "funding": np.linspace(0.01, 0.05, 500),
            "coin_oi": np.linspace(1000, 2000, 500),
            "dvol": np.linspace(50, 80, 500),
        }, index=index)
        first = score_p4.score_a2(frame)
        frame.loc[index[-1], "price"] = 10_000
        second = score_p4.score_a2(frame)
        self.assertEqual(first["up_building_h10"]["episodes"],
                         second["up_building_h10"]["episodes"])

    def test_scorer_refuses_the_commit_that_added_the_rule(self):
        # The guard stops when HEAD is the commit that added the rule, because
        # a rule and its score in one commit is not a pre-registered rule.
        real = score_p4.subprocess.run

        def same_commit(args, **kwargs):
            if args[:3] == ["git", "rev-parse", "HEAD"]:
                added = real(["git", "log", "--diff-filter=A", "--format=%H",
                              "--", score_p4.PREREG], cwd=score_p4.ROOT,
                             capture_output=True, text=True, check=True)
                return type("R", (), {"returncode": 0,
                                      "stdout": added.stdout.split()[0] + "\n"})()
            return real(args, **kwargs)

        score_p4.subprocess.run = same_commit
        try:
            with self.assertRaises(SystemExit):
                score_p4.prereg_commit()
        finally:
            score_p4.subprocess.run = real


if __name__ == "__main__":
    unittest.main()
