"""A daemon restarted by procmgr must find its libraries itself.

procmgr starts a daemon from a clean environment, and the venv does not carry
pandas. The libraries live in the user site. A script that imports pandas
before adding that directory dies on the first line, and the supervisor
restarts it every minute. The import has to succeed with the user site absent
from sys.path, which is what a restarted daemon sees.
"""

import importlib
import os
import sys
import unittest

_SITE = "/opt/data/.local/lib/python3.14/site-packages"

DAEMONS = [
    "scripts.funding_sum_daemon",
    "scripts.backfill_high_low",
    "scripts.pull_listed_history",
    "scripts.append_panel_xs",
]


class DaemonFindsLibraries(unittest.TestCase):
    def test_imports_with_user_site_absent(self):
        saved = list(sys.path)
        try:
            sys.path[:] = [p for p in sys.path if p != _SITE]
            for name in DAEMONS:
                sys.modules.pop(name, None)
                module = importlib.import_module(name)
                self.assertIn(_SITE, module.sys.path, name)
        finally:
            sys.path[:] = saved

    def test_a_count_is_not_a_file_list(self):
        # record_write takes the names of the files just written. Passing the
        # count walks the digits of the number and raises, which is what the
        # funding sum daemon did on its first cycle after the restart.
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
        import data_guard
        with self.assertRaises(TypeError):
            data_guard.record_write("data/panel_xs", 0, "funding_sum: daily funding sum")


if __name__ == "__main__":
    unittest.main()
