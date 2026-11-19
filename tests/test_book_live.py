"""book_live marks only legs the book still holds.

signals/book.csv keeps closed rows, with a close date in the closed column.
Marking those reports a paper return on a position that no longer exists.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import live_daemon  # noqa: E402


class BookLiveTests(unittest.TestCase):
    def test_closed_legs_are_not_marked(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "signals", "book.csv")
            os.makedirs(os.path.dirname(path))
            open(path, "w").write(
                "date,symbol,side,score,price,closed,close_price\n"
                "2026-11-05,PEPE,long,0.7,1.0,2026-11-12,0.9\n"
                "2026-11-05,OPEN,long,0.6,2.0,,\n")
            live_daemon.ROOT = tmp
            live = live_daemon.book_live({"PEPE": 0.5, "OPEN": 3.0})
        self.assertEqual([leg["symbol"] for leg in live["legs"]], ["OPEN"])
        self.assertEqual(live["paper_return"], 50.0)

    def test_no_open_legs_returns_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "signals", "book.csv")
            os.makedirs(os.path.dirname(path))
            open(path, "w").write(
                "date,symbol,side,score,price,closed,close_price\n"
                "2026-11-05,PEPE,long,0.7,1.0,2026-11-12,0.9\n")
            live_daemon.ROOT = tmp
            self.assertEqual(live_daemon.book_live({"PEPE": 0.5}), {})


class RsStaleRecordTests(unittest.TestCase):
    def test_cycle_records_the_reading_it_would_otherwise_lose(self):
        # The payload is force-pushed, so the previous health.rs_stale is gone
        # after the next cycle. A cycle that does not write the log leaves A5
        # with one reading and a span of zero, forever.
        with tempfile.TemporaryDirectory() as tmp:
            saved = {name: getattr(live_daemon, name)
                     for name in ("LOG", "append", "pull_5m", "board", "push",
                                  "hourly_closes", "TOP", "time")}
            live_daemon.LOG = os.path.join(tmp, "rs_stale_log.jsonl")
            recorded = []
            live_daemon.append = lambda path, ts, stale, age: recorded.append(
                (path, ts, stale, age)) or True
            try:
                live_daemon.pull_5m = lambda names, now: (0, now, {})
                live_daemon.board = lambda names: {"as_of": "2026-11-19T14:00:00Z"}
                live_daemon.push = lambda payload: True
                live_daemon.hourly_closes = lambda: {}
                live_daemon.time = type("T", (), {"time": staticmethod(lambda: 1795096800)})()
                live_daemon.TOP = os.path.join(tmp, "top.json")
                open(live_daemon.TOP, "w").write(json.dumps({"rows": []}))
                live_daemon.cycle({})
                self.assertEqual(len(recorded), 1)
                path, ts, stale, age = recorded[0]
                self.assertEqual(path, live_daemon.LOG)
                self.assertFalse(stale)
                self.assertRegex(ts, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
            finally:
                for name, value in saved.items():
                    setattr(live_daemon, name, value)


class BoardStampTests(unittest.TestCase):
    def test_board_stamps_the_last_closed_bar(self):
        # The refill already dropped the bar still forming, so the board reads
        # the last stored bar. Dropping it again reports an hour that is closed.
        with tempfile.TemporaryDirectory() as tmp:
            store = os.path.join(tmp, "intraday")
            os.makedirs(store)
            open(os.path.join(store, "BTCUSDT_PERP.A.csv"), "w").write(
                "t,o,h,l,c,v\n1794970800,1,1,1,1,1\n1794974400,1,1,1,2,1\n")
            daily = os.path.join(tmp, "daily.json")
            open(daily, "w").write(json.dumps([]))
            live_daemon.STORE_1H = store
            live_daemon.DAILY = daily
            board = live_daemon.board(["BTCUSDT_PERP.A"])
        self.assertEqual(board["as_of"], "2026-11-18T04:00:00Z")


if __name__ == "__main__":
    unittest.main()
