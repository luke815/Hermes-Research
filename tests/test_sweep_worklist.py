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
    def test_a_partial_measure_stays_pending_until_every_emittable_cell(self):
        # Conditioned variants are not this scorer's cells. ratio_btc is.
        # Saving the raw cell does not finish the measure.
        work = {
            "obv|raw|above|80|ret_1|pit_cross_section|none|daily",
            "obv|raw|above|80|ret_1|pit_cross_section|heat_tercile|daily",
            "obv|ratio_btc|above|80|ret_1|pit_cross_section|none|daily",
            "basis_level|raw|above|80|ret_1|pit_cross_section|none|daily",
        }
        done = {"obv|raw|above|80|ret_1|pit_cross_section|none|daily"}
        pending = sweep_xs.pending_measures(work, done, {"obv", "basis_level"})
        self.assertEqual(pending, ["basis_level", "obv"])
        done.add("obv|ratio_btc|above|80|ret_1|pit_cross_section|none|daily")
        pending = sweep_xs.pending_measures(work, done, {"obv", "basis_level"})
        self.assertEqual(pending, ["basis_level"])
        self.assertFalse(sweep_xs.emittable(
            "obv|raw|above|80|ret_1|pit_cross_section|heat_tercile|daily"))

    def test_status_line_counts_cells_against_the_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            sweep_xs.STATUS = os.path.join(tmp, "sweep_status")
            work = {"a|raw", "b|raw", "c|raw"}
            line = sweep_xs.status_line({"a|raw", "z|raw"}, work)
            self.assertIn("scored 1 of 3 testable, from ", line)
            self.assertTrue(line.endswith("counter.json"))
            self.assertEqual(open(sweep_xs.STATUS).read().strip(), line)

    def test_append_skips_cells_already_saved(self):
        # A measure pending only for ratio_btc still emits the cells the
        # previous scorer wrote. Those are skipped; the missing cell is kept.
        # A duplicate inside the new rows still refuses the write.
        import pandas as pd
        with tempfile.TemporaryDirectory() as tmp:
            sweep_xs.OUT = tmp
            saved = "obv|raw|above|80|ret_1|pit_cross_section|none|daily"
            missing = "obv|ratio_btc|above|80|ret_1|pit_cross_section|none|daily"
            rows = [{"id": saved, "measure": "obv"}, {"id": missing, "measure": "obv"}]
            path, total = sweep_xs.append_rows(rows, already={saved})
            written = pd.read_csv(path)
            self.assertEqual(list(written["id"]), [missing])
            self.assertEqual(total, 1)
            with self.assertRaises(RuntimeError):
                sweep_xs.append_rows(
                    [{"id": missing, "measure": "obv"}, {"id": missing, "measure": "obv"}],
                    already=set())

    def test_work_list_reads_the_enumerator_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cells.json")
            json.dump(["basis_level|raw|above|80|ret_1"], open(path, "w"))
            sweep_xs.WORK = path
            self.assertEqual(sweep_xs.work_list(), {"basis_level|raw|above|80|ret_1"})


if __name__ == "__main__":
    unittest.main()
