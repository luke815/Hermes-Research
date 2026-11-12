"""Append the Donchian-width verdict. Numbers come from the results file."""

import json
from pathlib import Path

result = json.loads(Path("results/2026-11-12_confirm_donchian_raw.json").read_text())
validation = result["validation"]
test = result["test"]
text = (
    "\n\nVerdict: rejected. Validation flips the train sign and misses the bar. "
    f"Train spread was {result['train_spread_pct']} percent over {result['train_n']} independent bars, t-stat {result['train_score']}. "
    f"Validation independent spread is {round(validation['spread_independent'] * 100, 4)} percent, Newey-West t-stat {round(validation['t_newey_west'], 4)}, "
    f"against a deflated bar of {result['deflated_bar']} from {result['family_combinations']} volatility combinations, and the "
    f"independent count is {validation['n_independent']}. The flipped sign holds in 2024 and in 2025. Test also flips: "
    f"the independent spread is {round(test['spread_independent'] * 100, 4)} percent, t-stat {round(test['t_newey_west'], 4)}, "
    f"over {test['n_independent']} independent bars, and 2026 carries the flipped sign. The test count is above 40, which does not "
    "rescue a validation that flipped the sign and missed the bar. The cell is closed. Its neighbours "
    "are not tried. The score is unchanged. Fifty-two tests since the last "
    "admission. results/2026-11-12_confirm_donchian_raw.json.\n"
)
path = Path("research/log.md")
path.write_text(path.read_text() + text)
print("appended", path.stat().st_size)
