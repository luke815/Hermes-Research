"""The sweep self-check must not fail on a file an older scorer wrote.

The check re-scores the newest file and compares to 1e-9. A file written
before the scorer changed which bars it counts cannot match, and raising on
that reports a code change as a data failure. A file with no period hash was
scored by an older scorer and is skipped.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SelfCheckSkipsOldFiles(unittest.TestCase):
    def test_a_file_without_a_period_hash_is_not_compared(self):
        from scripts.sweep_daemon import self_check
        result = self_check((None, None, None, None, "current-hash"))
        self.assertFalse(result["matched"])
        self.assertIn("older scorer", result["note"])


if __name__ == "__main__":
    unittest.main()
