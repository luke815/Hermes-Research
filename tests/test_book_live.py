"""book_live marks only legs the book still holds.

signals/book.csv keeps closed rows, with a close date in the closed column.
Marking those reports a paper return on a position that no longer exists.
"""

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


if __name__ == "__main__":
    unittest.main()
