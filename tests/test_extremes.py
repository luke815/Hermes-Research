"""The extremes lists rank one row per coin and keep a thin name out."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_extremes as extremes  # noqa: E402


def _write(folder, name, rows):
    path = os.path.join(folder, name)
    with open(path, "w") as handle:
        handle.write("date,close,volume_usd,oi_usd,funding_rate\n")
        for row in rows:
            handle.write(",".join(str(value) for value in row) + "\n")


def _bars(start, closes, funding, oi, volume):
    return [(f"2026-01-{day:02d}", closes[day - 1], volume, oi[day - 1], funding[day - 1])
            for day in range(1, len(closes) + 1)]


class Lists(unittest.TestCase):
    def test_a_thin_name_is_dropped_and_one_coin_appears_once(self):
        tmp = tempfile.TemporaryDirectory()
        closes = [100 + day for day in range(60)]
        funding = [0.0001] * 59 + [0.01]
        oi = [30_000_000] * 60
        _write(tmp.name, "binance_ZECUSDT.csv",
               _bars(0, closes, funding, oi, 20_000_000))
        _write(tmp.name, "bybit_ZECUSDT.csv",
               _bars(0, closes, funding, [10_000_000] * 60, 20_000_000))
        _write(tmp.name, "binance_THINUSDT.csv",
               _bars(0, closes, funding, [1_000_000] * 60, 20_000_000))
        payload = extremes.build(tmp.name)
        coins = [row["symbol"] for row in payload["lists"]["crowded_longs"]]
        self.assertEqual(coins, ["ZEC"])
        self.assertEqual(payload["universe_n"], 1)
        self.assertEqual(sorted(payload["lists"]), sorted(extremes.LISTS))
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
