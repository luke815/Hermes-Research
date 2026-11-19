"""The refill result is named where the scheduler cannot erase it.

The scheduler writes results/<date>_laevitas_refresh.json itself, so a result
written under that name is gone by the time anyone reads it. This calls the
script's record() with a writer it controls, and fails if the name or the
payload is wrong.
"""

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import laevitas_refresh as refresh  # noqa: E402


class Record(unittest.TestCase):
    def test_record_names_the_days_a_refill_wrote(self):
        today = datetime.now(timezone.utc).date().isoformat()
        day = (datetime.now(timezone.utc).date() - timedelta(days=2)).isoformat()
        seen = {}

        def writer(name, payload, inputs):
            seen["name"] = name
            seen["payload"] = payload
            seen["inputs"] = inputs
            return f"results/{today}_{name}.json"

        path = refresh.record(today, {"rr_btc": [day], "rr_eth": []}, writer)
        self.assertEqual(path, f"results/{today}_l10_refresh.json")
        self.assertEqual(seen["name"], "l10_refresh")
        self.assertNotEqual(seen["name"], "laevitas_refresh")
        self.assertEqual(seen["payload"]["refilled"], ["rr_btc"])
        self.assertEqual(seen["payload"]["filled"]["rr_btc"], [day])
        self.assertEqual(seen["payload"]["filled"]["rr_eth"], [])
        self.assertEqual(seen["inputs"], ["data/raw"])


if __name__ == "__main__":
    unittest.main()
