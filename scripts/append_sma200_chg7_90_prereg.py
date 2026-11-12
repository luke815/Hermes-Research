"""Pre-register the sma_200 confirmation. Writes no score.

The neighbour conclusion is filled from the check output, never typed.
"""

import json
from pathlib import Path

LOG = Path(__file__).resolve().parents[1] / "research" / "log.md"
CHECK = Path("/opt/data/cache/scratch/sma200_neighbour.json")
PICK = Path("/opt/data/cache/scratch/next_cell.json")


def main():
    check = json.loads(CHECK.read_text())
    pick = json.loads(PICK.read_text())
    if check["neighbour_hits"]:
        raise SystemExit("cell is a neighbour; do not pre-register: " + ",".join(check["neighbour_hits"]))
    if pick["cell_id"] != check["cell_id"]:
        raise SystemExit("pick and check disagree")
    recorded = ", ".join(
        f"{row['cell_id']} ({row['verdict']})" for row in check["recorded_sma_200"]
    ) or "none"
    text = f"""

## 2026-11-12, pre-registered before any computation: confirm sma_200 chg_7 above 90, BTC 3-day return

Candidate: confirm_sma_200_chg_7_above_90_ret_3_btc. Hypothesis: the 7-day change in the 200-day simple average, when it sits above its own trailing 90th percentile, precedes a higher 3-day BTC return net of costs, and that edge keeps the train sign on validation at a t-stat above the trend family deflated bar. Rule: cell sma_200|chg_7|above|90|ret_3|btc|none|daily. The live leaderboard, results/sweeps/leaderboard.json, was rewritten at 2026-11-12T05:00:13Z from results/sweeps/2026-11-12_xs.csv and its top row is breadth|xs_rank|above|90|rel_1|pit_cross_section|none|daily, a cross-sectional cell the confirmation procedure cannot score. This cell is the top unconfirmed cell in results/sweeps/2026-11-05.csv, the single-name train file, once cells already recorded in results/sweeps/confirmations.json are excluded, once a cell whose expected validation count is below 30 is excluded, and once neighbours of a closed cell are excluded. A neighbour is the same measure, universe and direction whose every difference is an adjacent threshold, an adjacent change lookback, an adjacent z-score window, or an adjacent horizon of the same kind. The recorded sma_200 cells are {recorded}. The closed cell uses threshold 80 against this cell's 90, and 80 and 90 are adjacent on the threshold ladder, so the neighbour check was run before this text was written. Its output, results of scripts/check_sma200_chg7_90.py, lists {len(check['neighbour_hits'])} neighbour hits across {check['record_rows']} recorded cells. The feature is lagged one bar and its percentile comes from past data only. The target is the 3-day forward return of BTC, net of the costs table at the thin tier. The statistic is the Newey-West t-stat with lag 3, counted on every third bar. Family N is the trend row count in results/sweeps/2026-11-05.csv, {pick['family_n']}, from the output of scripts/pick_from_trainfile.py written today. The deflated bar uses the count of distinct measure, target and universe combinations in that family, {pick['family_combinations']}, from the same output and from results/2026-11-06_confirmations_amended.json, and the bar is 2 + 0.5 log10({pick['family_combinations']}). Validation is 2024-07-01 to 2025-12-31 and test is 2026-01-01 onward. Pass: validation independent n at least 30, the validation spread keeps the train sign, and the validation t-stat clears the bar; the test period is reported and gates once it holds 40 independent observations. Fail: the validation sign flips, the validation t-stat misses the bar, or the test sign flips once its count clears 40. A validation count below 30 is insufficient and the cell is re-queued, not closed. No number has been computed. {pick['skipped_ahead']} cells rank above this one and each is already attempted, a neighbour of a closed cell, or expects fewer than 30 independent validation observations.

"""
    current = LOG.read_text()
    marker = "confirm sma_200 chg_7 above 90, BTC 3-day return"
    if marker in current:
        raise SystemExit("pre-registration already present")
    LOG.write_text(current + text)
    print(f"appended, lines now {LOG.read_text().count(chr(10))}")


if __name__ == "__main__":
    main()
