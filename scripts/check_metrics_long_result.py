"""Assert the long-metrics results file matches the saved series."""

import json
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester")
payload = json.loads((ROOT / "results" / "2026-11-04_d1_binance_metrics_long.json").read_text())
assert payload["symbols_in_slice"] == 16, payload["symbols_in_slice"]
assert payload["metrics_days_total"] == 12150, payload["metrics_days_total"]
assert payload["checksum_failures"] == 0
assert payload["blank_open_interest_days"] == 0
assert payload["days_with_a_blank_ratio"] == 1106
mismatches = [item for item in payload["per_symbol"] if not item["ends_match_listing"]]
assert [item["symbol"] for item in mismatches] == ["MATICUSDT"], mismatches
assert mismatches[0]["listing_first"] == "1993.zip"
assert mismatches[0]["first"] == "2021-12-01"
assert mismatches[0]["last"] == mismatches[0]["listing_last"] == "2025-01-22"
print("assertions ok")
print("ends_match", payload["symbols_whose_ends_match_listing"], "of", payload["symbols_in_slice"])
