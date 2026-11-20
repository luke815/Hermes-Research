"""The daily funding pull is percent per 8h, and the puller says so.

The daily file sits near 0.007 and the hourly file sits near 0.00004, a
hundredth of it. A daily pull saved on the hourly scale must be refused
before it is written, and a daily pull on the percent-per-8h scale must pass.
"""

import unittest

from scripts.fetch_laevitas import assert_daily_funding_scale


class DailyFundingScale(unittest.TestCase):
    def test_daily_median_passes(self):
        median = assert_daily_funding_scale([0.01, 0.007, -0.002, 0.012])
        self.assertAlmostEqual(median, 0.0085)

    def test_hourly_scale_is_refused(self):
        with self.assertRaises(ValueError):
            assert_daily_funding_scale([0.000057, 0.000064, 0.000038])

    def test_empty_pull_is_refused(self):
        with self.assertRaises(ValueError):
            assert_daily_funding_scale([])
