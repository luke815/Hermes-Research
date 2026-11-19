"""The delisted merge adds names and does not touch the ones already there."""

import json
import os
import shutil
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scripts.merge_delisted as merger  # noqa: E402


def _saved(day_millis, price):
    return {"items": [{"date": day_millis, "price": price, "volume": 10.0,
                       "volume_coin": 2.0, "funding": 0.01, "open_interest": 500.0,
                       "basis": -0.3, "long_short_ratio": 0.8}]}


class MergeDelistedTests(unittest.TestCase):
    def test_a_saved_name_is_added_and_an_existing_one_is_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            panel = os.path.join(tmp, "panel")
            store = os.path.join(tmp, "store")
            out = os.path.join(tmp, "out")
            os.makedirs(panel)
            os.makedirs(store)
            pd.DataFrame({"date": ["2026-11-01"], "close": [1.0]}).to_csv(
                os.path.join(panel, "binance_LIVEUSDT.csv"), index=False)
            json.dump(_saved(1633046400000, 9.0),
                      open(os.path.join(store, "BINANCE_LUNAUSDT.json"), "w"))
            json.dump(_saved(1633046400000, 3.0),
                      open(os.path.join(store, "BINANCE_LIVEUSDT.json"), "w"))
            json.dump({"items": []}, open(os.path.join(store, "OKX_EMPTY-USDT-SWAP.json"), "w"))
            counts = merger.merge(store, panel, out)
            written = sorted(os.listdir(out))
            self.assertEqual(written, ["binance_LIVEUSDT.csv", "binance_LUNAUSDT.csv"])
            self.assertEqual([row["panel"] for row in counts["added"]], ["binance_LUNAUSDT.csv"])
            kept = pd.read_csv(os.path.join(out, "binance_LIVEUSDT.csv"))
            self.assertEqual(list(kept["close"]), [1.0])
            added = pd.read_csv(os.path.join(out, "binance_LUNAUSDT.csv"))
            self.assertEqual(list(added.columns), merger.COLUMNS)
            self.assertEqual(added["date"].iloc[0], "2021-10-01")
            self.assertEqual(added["funding_rate"].iloc[0], 0.01)
            self.assertEqual(counts["skipped_empty"], ["OKX_EMPTY-USDT-SWAP.json"])
            shutil.rmtree(tmp, ignore_errors=True)
