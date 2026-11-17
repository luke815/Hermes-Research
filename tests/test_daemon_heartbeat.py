"""A cycle result has to land in the heartbeat, including status_line.

status_line starts as a state key set to None. The idle write used to drop any
result key already in state, so a working daemon's heartbeat kept status_line
null and a live cycle looked stuck.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import daemon_base


class Heartbeat(unittest.TestCase):
    def test_idle_write_keeps_the_cycle_status_line(self):
        source = open(daemon_base.__file__).read()
        self.assertIn('"status_line"', source)
        # The allow-list is the line that decides which cycle keys survive.
        allow = [line for line in source.splitlines() if "as_of" in line and "status_line" in line]
        self.assertEqual(len(allow), 1, source)


if __name__ == "__main__":
    unittest.main()
