"""Append one confirmation sentence to the backlog line.

Every number is read from the results file. The sentence is inserted after
the previous attempt's marker, which is found, not assumed.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "results" / "2026-11-12_confirm_sma200_chg7_90.json"
PATH = ROOT / "research" / "backlog.md"
MARKER = "results/2026-11-12_confirm_mfi14.json."


def main():
    row = json.loads(RESULT.read_text())
    validation = row["validation"]
    test = row["test"]
    sentence = (
        " Forty-ninth attempt 2026-11-12: "
        f"{row['cell_id']} insufficient, re-queued, not closed. Validation holds "
        f"{validation['n_independent']} independent bars, below 30, t-stat "
        f"{validation['t_newey_west']:.4f} against bar {row['deflated_bar']}. "
        f"Test spread {test['spread_independent'] * 100:.4f} percent, t-stat "
        f"{test['t_newey_west']:.4f}, independent n {test['n_independent']}, "
        "sign kept. Not scored. results/2026-11-12_confirm_sma200_chg7_90.json."
    )
    text = PATH.read_text()
    if sentence.strip() in text:
        raise SystemExit("already present")
    count = text.count(MARKER)
    if count != 1:
        raise SystemExit(f"marker count {count}")
    PATH.write_text(text.replace(MARKER, MARKER + sentence, 1))
    print("backlog updated", PATH.stat().st_size)


if __name__ == "__main__":
    main()
