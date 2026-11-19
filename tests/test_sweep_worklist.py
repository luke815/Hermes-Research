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

    def test_status_line_cites_the_shared_counter(self):
        with tempfile.TemporaryDirectory() as tmp:
            sweep_xs.STATUS = os.path.join(tmp, "sweep_status")
            from regime_tester import counter
            counter.COUNTER = os.path.join(tmp, "counter.json")
            counter.SWEEPS = tmp
            open(os.path.join(tmp, "2026-11-05.csv"), "w").write("id\na|raw\n")
            line = sweep_xs.status_line(set(), set())
            self.assertEqual(line, counter.status_text())
            self.assertIn("cells scored 1 since 2026-10-31, from ", line)
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
            # The caller named the saved id, and today's file already holds it.
            # That is the cell it counted, so the write skips it.
            again, total = sweep_xs.append_rows(rows, already={saved, missing})
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

    def test_the_floor_keeps_one_venue_and_drops_a_thin_name(self):
        import pandas as pd
        with tempfile.TemporaryDirectory() as tmp:
            sweep_xs.PANEL = tmp
            pd.DataFrame({"oi_usd": [20_000_000] * 60}).to_csv(
                os.path.join(tmp, "binance_AAAUSDT.csv"), index=False)
            pd.DataFrame({"oi_usd": [20_000_000] * 90}).to_csv(
                os.path.join(tmp, "bybit_AAAUSDT.csv"), index=False)
            pd.DataFrame({"oi_usd": [1_000] * 90}).to_csv(
                os.path.join(tmp, "binance_THINUSDT.csv"), index=False)
            kept = sweep_xs.liquid_names(
                ["binance_AAAUSDT", "bybit_AAAUSDT", "binance_THINUSDT"])
            self.assertEqual(kept, ["bybit_AAAUSDT"])

    def test_a_row_from_another_universe_does_not_close_the_cell(self):
        import pandas as pd
        with tempfile.TemporaryDirectory() as tmp:
            sweep_xs.OUT = tmp
            pd.DataFrame({"id": ["obv|raw|above|80|ret_1|pit_cross_section|none|daily"],
                          "names": [1024]}).to_csv(os.path.join(tmp, "2026-11-17_xs_vec.csv"), index=False)
            self.assertEqual(sweep_xs.scored_ids(names=219), set())
            self.assertEqual(
                sweep_xs.scored_ids(names=1024),
                {"obv|raw|above|80|ret_1|pit_cross_section|none|daily"})

    def test_a_row_from_another_universe_is_not_a_second_writer(self):
        # scored_ids drops a row from a different universe, so the caller
        # never names it. Today's file still holds it. That is the same cell
        # on an old universe, not a writer the caller did not see, and
        # refusing the write leaves the measure pending forever.
        import pandas as pd
        with tempfile.TemporaryDirectory() as tmp:
            sweep_xs.OUT = tmp
            cell = "obv|raw|above|80|ret_1|pit_cross_section|none|daily"
            pd.DataFrame({"id": [cell], "names": [1024]}).to_csv(
                os.path.join(tmp, "2026-11-17_xs_vec.csv"), index=False)
            pd.DataFrame({"id": [cell], "names": [219]}).to_csv(
                os.path.join(tmp, "2026-11-19_xs_vec.csv"), index=False)
            path, total = sweep_xs.append_rows(
                [{"id": cell, "measure": "obv", "names": 234}], already=set())
            written = pd.read_csv(path)
            self.assertEqual(list(written["names"]), [234])
            self.assertEqual(total, 1)
            self.assertEqual(list(pd.read_csv(
                os.path.join(tmp, "2026-11-17_xs_vec.csv"))["names"]), [1024])

    def test_status_line_names_the_count_and_the_rate(self):
        line = sweep_xs.status_line(set(), set(), names=321, rows_this_hour=5400)
        self.assertIn("names 321", line)
        self.assertIn("cells per hour 5400", line)
        self.assertIn("cells scored", line)


if __name__ == "__main__":
    unittest.main()
