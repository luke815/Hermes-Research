"""The panel close comes from the index when the vendor price field jumps."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import build_universe_laevitas as builder  # noqa: E402

DAY = 86_400_000


def item(n, price, index):
    return {"date": 1_700_000_000_000 + n * DAY, "price": price, "index": index}


class CloseFromIndex(unittest.TestCase):
    def test_a_jump_day_takes_the_index_not_the_price_field(self):
        items = [
            item(0, 5.8e-06, 0.0058),
            item(1, 5.73, 0.00573),
            item(2, 6.6e-06, 0.0066),
        ]
        closes = builder.closes_of(items)
        self.assertEqual(closes[0], 5.8e-06)
        self.assertAlmostEqual(closes[1], 0.00573)
        self.assertEqual(closes[2], 6.6e-06)

    def test_an_ordinary_move_keeps_the_price_field(self):
        items = [item(0, 100.0, 100.0), item(1, 110.0, 110.2)]
        self.assertEqual(builder.closes_of(items), [100.0, 110.0])

    def test_a_series_with_no_index_keeps_the_price_field(self):
        items = [item(0, 5.8e-06, None), item(1, 0.00573, None)]
        self.assertEqual(builder.closes_of(items), [5.8e-06, 0.00573])


if __name__ == "__main__":
    unittest.main()
