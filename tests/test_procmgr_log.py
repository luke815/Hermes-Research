"""A daemon log must not gain NUL padding when the daemon starts.

procmgr used to open the log before forking. The parent and the child then
shared one file offset, and a seek in one moved the other, so the next write
landed past the end of the file and the kernel filled the gap with NUL bytes.
Those bytes crashed readers of the log. The log is now opened after the fork,
so a start leaves no NULs.
"""

import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class LogNotPadded(unittest.TestCase):
    def test_a_start_appends_no_nul_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, TMPDIR=tmp)
            script = os.path.join(ROOT, "scripts", "procmgr.py")
            before = os.path.getsize(os.path.join(ROOT, "ops", "logs", "supervisor.log"))
            subprocess.run([sys.executable, script, "start", "supervisor",
                            "log padding check"], cwd=ROOT, env=env,
                           capture_output=True, text=True, timeout=30)
            data = open(os.path.join(ROOT, "ops", "logs", "supervisor.log"), "rb").read()
            added = data[before:]
            self.assertNotIn(b"\x00", added, "a start padded the log with NUL bytes")


if __name__ == "__main__":
    unittest.main()
