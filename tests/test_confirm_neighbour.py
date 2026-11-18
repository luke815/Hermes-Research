"""The confirmation queue skips a neighbour of a closed cell.

A closed cell is one with a rejected verdict. Its neighbour is the same
measure differing on one adjacent axis, and confirm_daemon.eligible drops it
before it is ever queued. A void row is not a closed cell, so a neighbour of
one stays eligible.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import confirm_daemon  # noqa: E402


class NeighbourQueue(unittest.TestCase):
    def test_a_neighbour_of_a_rejected_cell_is_not_queued(self):
        with tempfile.TemporaryDirectory() as tmp:
            confirm_daemon.BOARD = os.path.join(tmp, "board.json")
            confirm_daemon.RECORD = os.path.join(tmp, "record.json")
            closed = "sma_200|chg_7|above|80|ret_3|btc|none|daily"
            neighbour = "sma_200|chg_7|above|90|ret_3|btc|none|daily"
            unrelated = "obv|raw|above|80|ret_3|btc|none|daily"
            json.dump({"leaderboard": [
                {"cell_id": neighbour, "status": "eligible"},
                {"cell_id": unrelated, "status": "eligible"},
            ]}, open(confirm_daemon.BOARD, "w"))
            json.dump([{"cell_id": closed, "verdict": "rejected"}],
                      open(confirm_daemon.RECORD, "w"))
            queued = [row["cell_id"] for row in confirm_daemon.eligible()]
            self.assertNotIn(neighbour, queued)
            self.assertIn(unrelated, queued)

    def test_a_neighbour_of_a_void_cell_stays_queued(self):
        with tempfile.TemporaryDirectory() as tmp:
            confirm_daemon.BOARD = os.path.join(tmp, "board.json")
            confirm_daemon.RECORD = os.path.join(tmp, "record.json")
            voided = "sma_200|chg_7|above|80|ret_3|btc|none|daily"
            neighbour = "sma_200|chg_7|above|90|ret_3|btc|none|daily"
            json.dump({"leaderboard": [{"cell_id": neighbour, "status": "eligible"}]},
                      open(confirm_daemon.BOARD, "w"))
            json.dump([{"cell_id": voided, "verdict": "void"}],
                      open(confirm_daemon.RECORD, "w"))
            queued = [row["cell_id"] for row in confirm_daemon.eligible()]
            self.assertIn(neighbour, queued)


if __name__ == "__main__":
    unittest.main()
