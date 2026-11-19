"""The hosted-page check accepts the lists in any order.

summary() sorts the list names, so a comparison against the spec's own order
fails on a page that serves every list. The old comparison did exactly that,
and a page returning 200 with all ten lists was recorded as not serving them.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import e3_check


class PagesServesKey(unittest.TestCase):
    def test_all_ten_lists_in_any_order_count_as_served(self):
        document = {"extremes": {"as_of": "2026-11-16", "universe_n": 1,
                                 "lists": {name: [] for name in reversed(e3_check.LISTS)}}}
        got = e3_check.summary(document)["lists_present"]
        self.assertEqual(got, sorted(e3_check.LISTS))
        # The comparison the check uses. Against the unsorted tuple it fails.
        self.assertNotEqual(got, list(e3_check.LISTS))
        self.assertEqual(got, sorted(e3_check.LISTS))

    def test_a_missing_list_is_not_served(self):
        lists = {name: [] for name in e3_check.LISTS}
        del lists["squeezes"]
        got = e3_check.summary({"extremes": {"lists": lists}})["lists_present"]
        self.assertNotEqual(got, sorted(e3_check.LISTS))


if __name__ == "__main__":
    unittest.main()
