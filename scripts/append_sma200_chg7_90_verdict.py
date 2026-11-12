"""Append the verdict for the sma_200 chg_7 above 90 confirmation.

Every number is read from the results file written today. Nothing is typed.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "results" / "2026-11-12_confirm_sma200_chg7_90.json"
PICK = Path("/opt/data/cache/scratch/next_cell.json")
LOG = ROOT / "research" / "log.md"


def pct(value):
    return f"{value * 100:.4f}"


def main():
    row = json.loads(RESULT.read_text())
    pick = json.loads(PICK.read_text())
    if row["verdict"] != "insufficient":
        raise SystemExit(f"unexpected verdict {row['verdict']}")
    if row["cell_id"] != pick["cell_id"]:
        raise SystemExit("results file is for a different cell")
    validation = row["validation"]
    test = row["test"]
    if validation["n_independent"] >= 30:
        raise SystemExit("validation count is not below the floor")
    years = ", ".join(f"{year} carries the flipped sign" for year, sign in validation["year_signs"].items() if sign < 0)
    text = (
        f"\nVerdict: insufficient, re-queued, not closed. Validation holds "
        f"{validation['n_independent']} independent bars, below 30. Train spread was "
        f"{pick['train_spread_pct']} percent over {pick['train_n']} independent bars, "
        f"t-stat {pick['train_score']}. Validation independent spread is "
        f"{pct(validation['spread_independent'])} percent, Newey-West t-stat "
        f"{validation['t_newey_west']:.4f}, against a deflated bar of {row['deflated_bar']} "
        f"from {row['family_combinations']} trend combinations, and {years}. Test keeps the "
        f"train sign at {pct(test['spread_independent'])} percent, t-stat "
        f"{test['t_newey_west']:.4f}, over {test['n_independent']} independent bars, and "
        f"2026 carries the train sign. Neither period is scored as a pass or a fail, because "
        f"the validation count is below the re-queue floor. The cell stays open and is not "
        f"closed. Its neighbours are not tried in this run. The score is unchanged. "
        f"Forty-eight tests since the last admission; this attempt does not add to that count. "
        f"results/2026-11-12_confirm_sma200_chg7_90.json.\n"
    )
    current = LOG.read_text()
    tail = current.rstrip().splitlines()[-1]
    if "No number has been computed." not in tail:
        raise SystemExit("log tail is not the pre-registration")
    LOG.write_text(current.rstrip() + "\n" + text)
    print("verdict appended")
    print(text)


if __name__ == "__main__":
    main()
