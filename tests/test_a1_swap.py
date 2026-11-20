"""The panel swap waits until the append job has stopped writing."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import a1_swap  # noqa: E402


class SwapWaits(unittest.TestCase):
    def test_a_live_append_blocks_the_swap(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "panel_append.pid")
            with open(path, "w") as handle:
                handle.write(str(os.getpid()))
            self.assertTrue(a1_swap.append_running(path))

    def test_a_dead_append_does_not_block_the_swap(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "panel_append.pid")
            with open(path, "w") as handle:
                handle.write("999999999")
            self.assertFalse(a1_swap.append_running(path))
            missing = os.path.join(tmp, "absent.pid")
            self.assertFalse(a1_swap.append_running(missing))


if __name__ == "__main__":
    unittest.main()
