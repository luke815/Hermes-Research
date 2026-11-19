"""The candidates key keeps five cells a family and drops a thin cell."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_candidates as candidates  # noqa: E402


def _row(family_measure, number, n, t_stat, degenerate=False):
    return {
        "id": f"{family_measure}|raw|above|80|ret_1|pit_cross_section|none|daily",
        "measure": family_measure, "transform": "raw", "direction": "above",
        "threshold": 80, "target": "ret_1", "universe": "pit_cross_section",
        "spread_independent": -0.01, "t_newey_west": t_stat,
        "n_independent": n, "below_minimum": n < 40, "degenerate": degenerate,
        "duplicate": False,
    }


class Selection(unittest.TestCase):
    def test_five_per_family_and_a_thin_cell_is_dropped(self):
        rows = [_row("rsi_14", i, 100, 5 - i * 0.1) for i in range(7)]
        rows.append(_row("sma_20", 1, 10, 9.0))
        rows.append(_row("obv", 1, 100, 4.0, degenerate=True))
        chosen = candidates.top_per_family(pd.DataFrame(rows))
        momentum = [row for row in chosen if row["family"] == "momentum"]
        self.assertEqual(len(momentum), 5)
        self.assertTrue(all(row["train_n"] >= 30 for row in chosen))
        self.assertTrue(all(row["family"] != "volume" for row in chosen))
        self.assertEqual(momentum[0]["side"], "fade")
        self.assertGreater(abs(momentum[0]["train_t"]), abs(momentum[-1]["train_t"]))

    def test_a_low_reading_is_not_signalled_above(self):
        self.assertFalse(candidates._signalled(0.05, "above"))
        self.assertTrue(candidates._signalled(0.95, "above"))
        self.assertTrue(candidates._signalled(-0.2, "below"))
        self.assertFalse(candidates._signalled(None, "above"))

    def test_last_closed_day_is_the_date_most_names_share(self):
        tmp = tempfile.TemporaryDirectory()
        pd.DataFrame({"date": ["2026-11-16", "2026-11-17"]}).to_csv(
            os.path.join(tmp.name, "binance_BTCUSDT.csv"), index=False)
        pd.DataFrame({"date": ["2026-11-17"]}).to_csv(
            os.path.join(tmp.name, "bybit_ETHUSDT.csv"), index=False)
        self.assertEqual(candidates._last_closed(tmp.name), "2026-11-17")
        tmp.cleanup()

    def test_a_tail_read_keeps_the_last_rows(self):
        tmp = tempfile.TemporaryDirectory()
        path = os.path.join(tmp.name, "one.csv")
        pd.DataFrame({"date": [f"2026-01-{i:02d}" for i in range(1, 21)],
                      "close": range(20), "unused": range(20)}).to_csv(path, index=False)
        tail = candidates._tail(path, rows=5)
        self.assertEqual(list(tail["close"]), [15, 16, 17, 18, 19])
        self.assertNotIn("unused", tail.columns)
        tmp.cleanup()

    def test_shadow_file_is_created_once(self):
        tmp = tempfile.TemporaryDirectory()
        path = os.path.join(tmp.name, "shadow.csv")
        cells = [{"cell_id": "m|raw|above|80|ret_1|pit_cross_section|none|daily"}]
        self.assertTrue(candidates.start_shadow(cells, "2026-11-16", path))
        self.assertFalse(candidates.start_shadow(cells, "2026-11-17", path))
        self.assertIn("2026-11-16", open(path).read())
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
