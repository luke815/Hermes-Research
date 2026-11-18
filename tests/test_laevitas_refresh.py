"""A deleted day is refilled by the next run, with no model action."""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import laevitas_refresh as refresh  # noqa: E402


def _ms(day):
    return int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


class Refill(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        refresh.STORE = self.tmp.name
        refresh.SERIES = (("rr_btc", "/historical/options/type/risk_reversal/deribit/BTC/25d"),)

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_deleted_day_is_requested_again(self):
        today = datetime.now(timezone.utc).date().isoformat()
        window = refresh.days(today)
        kept = [window[0], window[2]]
        json.dump([{"date": _ms(day), "30": 1.0} for day in kept],
                  open(os.path.join(self.tmp.name, "rr_btc_a.json"), "w"))
        asked = []

        def getter(url, headers, timeout, allowance):
            asked.append(url)
            return {"items": [{"date": _ms(window[1]), "30": 2.0}]}

        filled = refresh.refill(today, getter)
        self.assertEqual(filled["rr_btc"], [window[1]])
        self.assertEqual(len(asked), 1)
        saved = json.load(open(os.path.join(self.tmp.name, "rr_btc_gap.json")))
        self.assertEqual(saved[0]["30"], 2.0)

    def test_a_complete_window_makes_no_request(self):
        today = datetime.now(timezone.utc).date().isoformat()
        window = refresh.days(today)
        json.dump([{"date": _ms(day), "30": 1.0} for day in window],
                  open(os.path.join(self.tmp.name, "rr_btc_a.json"), "w"))

        def getter(url, headers, timeout, allowance):
            raise AssertionError("nothing was missing")

        filled = refresh.refill(today, getter)
        self.assertEqual(filled["rr_btc"], [])


if __name__ == "__main__":
    unittest.main()
