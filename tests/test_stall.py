"""The stall check names the top item without a verdict, and the digest reads it.

A blocked item has no verdict, so it is the top item until it is done. A
rejected item is closed. The digest's top-item line comes from the health log,
so the two cite the same item and the same run count.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import hourly_health  # noqa: E402
import digest_counter  # noqa: E402


BACKLOG = """# Backlog

- A1. Data integrity. Blocked 2026-11-19: the daemon walks the names.
- A2. Reopened 2026-11-18. Done 2026-11-18. done_check 735fd0c14d.
- C8. Liquidation cascade. Rejected 2026-11-18. The spread flips sign.
- C9. Cross-sectional momentum. Insufficient 2026-11-18. No dates in train.
- L0. The stall alert. Done when the health check log shows the check running.
"""


class StallCheck(unittest.TestCase):
    def test_a_blocked_item_is_the_top_and_a_rejected_one_is_not(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "research").mkdir()
        (root / "research" / "backlog.md").write_text(BACKLOG)
        (root / "ops").mkdir()
        (root / "ops" / "health.log").write_text(
            "2026-11-19T04:00:00Z stall_check item=A1 runs=1 top=- A1.\n")
        hourly_health.ROOT = root
        posted = []
        hourly_health.scheduler = type("S", (), {"post": staticmethod(lambda text: posted.append(text))})()

        top = hourly_health.stall_check()

        self.assertTrue(top.startswith("- A1."), top)
        logged = (root / "ops" / "health.log").read_text().splitlines()
        self.assertIn("item=A1", logged[-1])
        self.assertIn("runs=2", logged[-1])
        self.assertEqual(posted, [])

    def test_six_runs_posts_a_stall(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "research").mkdir()
        (root / "research" / "backlog.md").write_text(BACKLOG)
        (root / "ops").mkdir()
        prior = "".join(
            f"2026-11-19T0{n}:00:00Z stall_check item=A1 runs={n} top=- A1.\n" for n in range(1, 6))
        (root / "ops" / "health.log").write_text(prior)
        hourly_health.ROOT = root
        posted = []

        class Stub:
            @staticmethod
            def post(text):
                posted.append(text)

        sys.modules["scheduler"] = Stub()
        self.addCleanup(lambda: sys.modules.pop("scheduler", None))

        hourly_health.stall_check()

        self.assertEqual(len(posted), 1)
        self.assertIn("A1", posted[0])
        self.assertIn("6", posted[0])

    def test_digest_reads_the_health_log(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        log = os.path.join(tmp.name, "ops", "health.log")
        os.makedirs(os.path.dirname(log))
        with open(log, "w") as handle:
            handle.write("2026-11-19T05:00:00Z stall_check item=A1 runs=4 top=- A1.\n")
        saved = digest_counter.ROOT_DIR
        digest_counter.ROOT_DIR = tmp.name
        self.addCleanup(setattr, digest_counter, "ROOT_DIR", saved)

        self.assertEqual(digest_counter.top_item_line(), "top backlog item A1, 4 runs")


if __name__ == "__main__":
    unittest.main()
