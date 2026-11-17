"""The cross-section sweep takes its work from the enumerator's cell list.

A daemon that decides it is done from its own files reports remaining 0 while
the testable list still holds unscored cells. These tests pin the rule: a
measure is pending while one of its cells on the list is unscored, and the
status line counts scored cells against that list.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import sweep_xs


class WorkList(unittest.TestCase):
    def test_a_scored_measure_is_done_even_with_conditioned_variants(self):
        work = {"obv|raw|above|80|ret_1", "obv|raw|above|80|ret_1|heat_tercile",
                "basis_level|raw|above|80|ret_1"}
        done = {"obv|raw|above|80|ret_1"}
        done_measures = {cid.split("|", 1)[0] for cid in done}
        pending = sorted({cid.split("|", 1)[0] for cid in work - done
                          if cid.split("|", 1)[0] not in done_measures})
        self.assertEqual(pending, ["basis_level"])
        self.assertEqual(len(done & work), 1)

    def test_status_line_counts_cells_against_the_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            sweep_xs.STATUS = os.path.join(tmp, "sweep_status")
            work = {"a|raw", "b|raw", "c|raw"}
            line = sweep_xs.status_line({"a|raw", "z|raw"}, work)
            self.assertEqual(line, "scored 1 of 3 testable")
            self.assertEqual(open(sweep_xs.STATUS).read().strip(), line)

    def test_work_list_reads_the_enumerator_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cells.json")
            json.dump(["basis_level|raw|above|80|ret_1"], open(path, "w"))
            sweep_xs.WORK = path
            self.assertEqual(sweep_xs.work_list(), {"basis_level|raw|above|80|ret_1"})


if __name__ == "__main__":
    unittest.main()
