"""Append the stc ret_1 verdict and the backlog note.

Every number is read from the results file written this session.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "research" / "log.md"
BACKLOG = ROOT / "research" / "backlog.md"
RESULTS = ROOT / "results" / "2026-11-10_confirm_stc_ret_1.json"

row = json.loads(RESULTS.read_text())
validation = row["validation"]
test = row["test"]


def pct(value):
    return round(float(value) * 100, 4)


verdict = (
    "\nVerdict: rejected. Validation keeps the train sign but misses the bar. "
    f"Train spread was {row['train_spread_pct']} percent over {row['train_n']} "
    f"independent bars, t-stat {row['train_score']}. Validation independent spread is "
    f"{pct(validation['spread_independent'])} percent, Newey-West t-stat "
    f"{round(validation['t_newey_west'], 4)}, against a deflated bar of "
    f"{row['deflated_bar']} from {row['family_combinations']} trend combinations, "
    f"and the independent count is {validation['n_independent']}. The sign holds "
    "in 2024 and in 2025. Test flips the train sign at "
    f"{pct(test['spread_independent'])} percent, t-stat "
    f"{round(test['t_newey_west'], 4)}, over {test['n_independent']} independent bars, "
    "and 2026 carries the flipped sign. The test count clears 40, which does not rescue "
    "a validation that missed the bar. The cell is closed. Its neighbours are not tried. "
    "The score is unchanged. Thirty-two tests since the last admission. "
    "results/2026-11-10_confirm_stc_ret_1.json.\n"
)

note = (
    " Twenty-second attempt 2026-11-10: stc|chg_7|above|80|ret_1|eth|none|daily "
    f"rejected. Validation t-stat {round(validation['t_newey_west'], 4)} against bar "
    f"{row['deflated_bar']}, independent n {validation['n_independent']}, sign kept. "
    f"Test spread {pct(test['spread_independent'])} percent, t-stat "
    f"{round(test['t_newey_west'], 4)}, independent n {test['n_independent']}, sign flipped. "
    "Closed. results/2026-11-10_confirm_stc_ret_1.json."
)


def main():
    current = LOG.read_text()
    marker = "Verdict: rejected. Validation keeps the train sign but misses the bar. Train spread was -0.7374"
    if marker in current:
        raise SystemExit("verdict already present")
    LOG.write_text(current + verdict)
    backlog = BACKLOG.read_text()
    needle = "results/2026-11-10_confirm_rsi_14.json."
    if needle not in backlog:
        raise SystemExit("backlog needle not found")
    BACKLOG.write_text(backlog.replace(needle, needle + note, 1))
    print("log lines", LOG.read_text().count("\n"))
    print("backlog has note", note[:48] in BACKLOG.read_text())


if __name__ == "__main__":
    main()
