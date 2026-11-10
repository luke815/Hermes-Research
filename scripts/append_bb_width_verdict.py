"""Append the bb_width verdict and the backlog note.

Every number is read from the results file written this session.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "research" / "log.md"
BACKLOG = ROOT / "research" / "backlog.md"
RESULTS = ROOT / "results" / "2026-11-10_confirm_bb_width.json"

row = json.loads(RESULTS.read_text())
validation = row["validation"]
test = row["test"]


def pct(value):
    return round(float(value) * 100, 4)


verdict = (
    "\nVerdict: rejected. Validation flips the train sign and misses the bar. "
    f"Train spread was {row['train_spread_pct']} percent over {row['train_n']} "
    f"independent bars, t-stat {row['train_score']}. Validation independent spread is "
    f"{pct(validation['spread_independent'])} percent, Newey-West t-stat "
    f"{round(validation['t_newey_west'], 4)}, against a deflated bar of "
    f"{row['deflated_bar']} from {row['family_combinations']} volatility combinations, "
    f"and the independent count is {validation['n_independent']}. The flipped sign holds "
    "in 2024 and in 2025. Test also flips: the independent spread is "
    f"{pct(test['spread_independent'])} percent, t-stat "
    f"{round(test['t_newey_west'], 4)}, over {test['n_independent']} independent bars, "
    "and 2026 carries the flipped sign. The count is below 40, which does not make a "
    "flipped sign pending, and a failed validation is not rescued either way. The cell "
    "is closed. Its neighbours are not tried. The score is unchanged. Thirty-three tests "
    "since the last admission. results/2026-11-10_confirm_bb_width.json.\n"
)

note = (
    " Twenty-third attempt 2026-11-10: bb_width|z_90|above|80|ret_3|btc|none|daily "
    f"rejected. Validation t-stat {round(validation['t_newey_west'], 4)} against bar "
    f"{row['deflated_bar']}, independent n {validation['n_independent']}, sign flipped. "
    f"Test spread {pct(test['spread_independent'])} percent, t-stat "
    f"{round(test['t_newey_west'], 4)}, independent n {test['n_independent']}, sign flipped. "
    "Closed. results/2026-11-10_confirm_bb_width.json."
)


def main():
    current = LOG.read_text()
    marker = "Verdict: rejected. Validation flips the train sign and misses the bar. Train spread was 1.3435"
    if marker in current:
        raise SystemExit("verdict already present")
    LOG.write_text(current + verdict)
    backlog = BACKLOG.read_text()
    needle = "results/2026-11-10_confirm_stc_ret_1.json."
    if needle not in backlog:
        raise SystemExit("backlog needle not found")
    if note[:40] in backlog:
        raise SystemExit("backlog note already present")
    BACKLOG.write_text(backlog.replace(needle, needle + note, 1))
    print("log lines", LOG.read_text().count("\n"))
    print("backlog has note", note[:48] in BACKLOG.read_text())


if __name__ == "__main__":
    main()
