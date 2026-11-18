"""The daily liquidation sum adds the events, and a quiet day is absent."""

import json
import os
import tempfile
import unittest

import scripts.liq_daily_sum as summer


class LiqDailySum(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        summer.STORE = os.path.join(self.root, "store")

    def test_rest_rows_are_read_from_data(self):
        rows, meta = summer.rows_of({"data": [{"position_side": "long", "amount_usd": 3}],
                                     "meta": {"next_cursor": None}})
        self.assertEqual(len(rows), 1)
        self.assertIsNone(meta["next_cursor"])

    def test_two_events_sum_to_their_total(self):
        rows = [{"position_side": "long", "amount_usd": 100.0},
                {"position_side": "short", "amount_usd": 40.5}]
        got = summer.sum_events(rows)
        self.assertEqual(got["long"], 100.0)
        self.assertEqual(got["short"], 40.5)
        self.assertEqual(got["total"], 140.5)
        self.assertEqual(got["events"], 2)

    def test_a_day_with_no_events_is_absent(self):
        self.assertIsNone(summer.sum_events([]))
        summer.day_list = lambda today: ["2021-11-20", "2021-11-21"]
        summer.record_empty("BTC", "2021-11-20")
        saved = json.load(open(summer.path_for("BTC", "2021-11-20")))
        self.assertNotIn("2021-11-20", saved.get("days", {}))
        nxt = summer.pending("2021-11-22")
        self.assertEqual(nxt, ("BTC", "2021-11-21"))

    def test_the_sample_file_keeps_its_midnight_note(self):
        import scripts.liq_history_pull as pull
        pull.STORE = os.path.join(self.root, "sample")
        pull.save_page("BTC", "2021-11-20", "2022-11-19", 1, {
            "data": {"items": [{"date": 1, "side": "long", "usd_amount": 5}],
                     "meta": {"total": 1, "items": 1, "total_pages": 1}}})
        body = json.load(open(pull.path_for("BTC", "2021-11-20")))
        self.assertEqual(body["note"], "midnight sample, not a daily sum")
        self.assertEqual(body["items"][0]["usd_amount"], 5)


if __name__ == "__main__":
    unittest.main()
