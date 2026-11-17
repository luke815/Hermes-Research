"""A panel file must be sorted, closed, and funded by the day's sum.

A descending file would make every rolling measure read the future as the
past, so the reader refuses one. A bar dated today has not closed, because
bars are stamped with their open time. The funding sum is the day's
settlements added, not the last print times the count.
"""

import unittest

import pandas as pd

from regime_tester.panel_integrity import assert_sorted, clean_frame, sum_funding


class PanelIntegrity(unittest.TestCase):
    def test_descending_file_fails(self):
        frame = pd.DataFrame(
            {"date": ["2026-11-16", "2026-11-15", "2026-11-14"], "close": [1, 2, 3]})
        with self.assertRaises(AssertionError):
            assert_sorted(frame)

    def test_clean_sorts_and_drops_today(self):
        frame = pd.DataFrame({
            "date": ["2026-11-17", "2026-11-17", "2026-11-18", "2026-11-15"],
            "close": [2.0, 9.0, 5.0, 1.0],
        })
        cleaned = clean_frame(frame, today="2026-11-17")
        self.assertEqual(list(cleaned["date"]), ["2026-11-15"])
        self.assertEqual(list(cleaned["close"]), [1.0])
        assert_sorted(cleaned)

    def test_funding_sum_is_not_the_last_print_times_the_count(self):
        # Three settlements on one day, 8 hours apart. The last print times
        # the count is 0.0003; the sum of the prints is 0.0004.
        day = 1_794_787_200_000  # 2026-11-16 00:00:00 UTC
        hour = 3_600_000
        prints = [(day, 0.0001), (day + 8 * hour, 0.0002), (day + 16 * hour, 0.0001)]
        summed = sum_funding(prints, 8)
        self.assertEqual(list(summed), ["2026-11-16"])
        self.assertAlmostEqual(summed["2026-11-16"]["funding_rate"], 0.0004)
        self.assertEqual(summed["2026-11-16"]["funding_count"], 3)
        self.assertEqual(summed["2026-11-16"]["funding_interval_hours"], 8)
        last_times_count = 0.0001 * 3
        self.assertNotAlmostEqual(summed["2026-11-16"]["funding_rate"], last_times_count)

    def test_a_blank_day_is_absent(self):
        summed = sum_funding([], 8)
        self.assertEqual(summed, {})


if __name__ == "__main__":
    unittest.main()
