"""The liquidation history puller resumes and does not double a page."""

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone

import scripts.liq_history_pull as pull


class LiqHistory(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        pull.STORE = os.path.join(self.root, "store")
        pull.PROGRESS = os.path.join(self.root, "progress.json")

    def test_a_saved_page_is_not_refetched(self):
        pull.save_page("BTC", "2021-11-20", "2022-11-19", 1, {
            "data": {"items": [{"date": i, "side": "long"} for i in range(1440)],
                     "meta": {"total": 2000, "items": 1440, "total_pages": 2}}})
        nxt = pull.pending_page("2022-11-19")
        self.assertEqual(nxt[:4], ("BTC", "2021-11-20", "2022-11-19", 2))

    def test_a_finished_window_moves_to_the_next(self):
        pull.save_page("BTC", "2021-11-20", "2022-11-19", 1, {
            "data": {"items": [{"date": 1, "side": "long"}],
                     "meta": {"total": 1, "items": 1, "total_pages": 1}}})
        nxt = pull.pending_page("2022-11-19")
        self.assertEqual(nxt[0], "ETH")

    def test_saving_a_page_twice_does_not_double_the_rows(self):
        payload = {"data": {"items": [{"date": 1, "side": "short", "usd_amount": 5}],
                            "meta": {"total": 1, "items": 1, "total_pages": 1}}}
        pull.save_page("ETH", "2021-11-20", "2022-11-19", 1, payload)
        pull.save_page("ETH", "2021-11-20", "2022-11-19", 1, payload)
        body = json.load(open(pull.path_for("ETH", "2021-11-20")))
        self.assertEqual(len(body["items"]), 1)
        self.assertIn("midnight sample", body["note"])

    def test_a_short_page_is_refetched(self):
        pull.save_page("BTC", "2021-11-20", "2022-11-19", 1, {
            "data": {"items": [{"date": 1, "side": "long"}],
                     "meta": {"total": 692, "items": 10, "total_pages": 70}}})
        nxt = pull.pending_page("2022-11-19")
        self.assertEqual(nxt[3], 1)

    def test_windows_stop_at_today(self):
        spans = pull.windows("2023-01-01")
        self.assertEqual(spans[0], ("2021-11-20", "2022-11-19"))
        self.assertLessEqual(spans[-1][1], "2023-01-01")
        self.assertGreater(len(spans), 1)


if __name__ == "__main__":
    unittest.main()
