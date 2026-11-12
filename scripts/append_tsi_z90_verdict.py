"""Append the TSI 90-bar verdict. Reads the results file written today. Scores nothing."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "results" / "2026-11-12_confirm_tsi_z90.json"
LOG = ROOT / "research" / "log.md"


def pct(value):
    return f"{value * 100:.4f}"


def main():
    row = json.loads(RESULT.read_text())
    val = row["validation"]
    test = row["test"]
    text = (
        "\nVerdict: rejected. Validation keeps the train sign but misses the bar. "
        f"Train spread was {row['train_spread_pct']} percent over {row['train_n']} independent bars, "
        f"t-stat {row['train_score']}. Validation independent spread is {pct(val['spread_independent'])} percent, "
        f"Newey-West t-stat {val['t_newey_west']:.4f}, against a deflated bar of {row['deflated_bar']} "
        f"from {row['family_combinations']} momentum combinations, and the independent count is "
        f"{val['n_independent']}. The sign flips in 2024 and holds in 2025. Test keeps the train sign at "
        f"{pct(test['spread_independent'])} percent, t-stat {test['t_newey_west']:.4f}, over "
        f"{test['n_independent']} independent bars, and 2026 carries the train sign. The test count is below 40, "
        "which does not rescue a validation that missed the bar. The cell is closed. Its neighbours are not tried. "
        "The score is unchanged. Fifty tests since the last admission. "
        "results/2026-11-12_confirm_tsi_z90.json.\n"
    )
    current = LOG.read_text()
    if "results/2026-11-12_confirm_tsi_z90.json" in current:
        raise SystemExit("verdict already present")
    LOG.write_text(current + text)
    print(f"appended, lines now {LOG.read_text().count(chr(10))}")


if __name__ == "__main__":
    main()
