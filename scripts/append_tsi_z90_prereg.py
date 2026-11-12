"""Pre-register the TSI 90-bar confirmation. Writes no score."""

from pathlib import Path

LOG = Path(__file__).resolve().parents[1] / "research" / "log.md"

TEXT = """

## 2026-11-12, pre-registered before any computation: confirm tsi z_90 below 5, ETH 1-day return

Candidate: confirm_tsi_z_90_below_5_ret_1_eth. Hypothesis: the true strength index, when its trailing 90-bar z-score sits below its own 5th percentile, precedes a higher 1-day ETH return net of costs, and that edge keeps the train sign on validation at a t-stat above the momentum family deflated bar. Rule: cell tsi|z_90|below|5|ret_1|eth|none|daily. The live leaderboard, results/sweeps/leaderboard.json, was rewritten at 2026-11-12T07:01:13Z from results/sweeps/2026-11-12_xs.csv and its top row is breadth|xs_rank|above|90|rel_1|pit_cross_section|none|daily, a cross-sectional cell the confirmation procedure cannot score. This cell is the top unconfirmed cell in results/sweeps/2026-11-05.csv, the single-name train file, once cells already recorded in results/sweeps/confirmations.json are excluded, once a cell whose expected validation count is below 30 is excluded, and once neighbours of a closed cell are excluded. A neighbour is the same measure, universe and direction whose every difference is an adjacent threshold, an adjacent change lookback, an adjacent z-score window, or an adjacent horizon of the same kind. The one recorded tsi cell is tsi|z_30|below|20|ret_3|eth|none|daily, which is closed. Its z-score window is 30 bars rather than 90, and 30 and 90 are adjacent on the z-score ladder, but the threshold, the target kind and the horizon also differ, so the neighbour rule does not connect it. The neighbour check, scripts/check_tsi_z90_neighbour.py, lists 0 neighbour hits. Twenty-seven cells rank above this one and each is already attempted, a neighbour of a closed cell, or expects fewer than 30 independent validation observations. The feature is lagged one bar and its percentile comes from past data only. The target is the 1-day forward return of ETH, net of the costs table at the thin tier. The statistic is the Newey-West t-stat with lag 1, counted on every bar. Family N is the momentum row count in results/sweeps/2026-11-05.csv, 6498, from the output of scripts/pick_from_trainfile.py written today. The deflated bar uses the count of distinct measure, target and universe combinations in that family, 126, from the same output and from results/2026-11-06_confirmations_amended.json, and the bar is 2 + 0.5 log10(126). Validation is 2024-07-01 to 2025-12-31 and test is 2026-01-01 onward. Pass: validation independent n at least 30, the validation spread keeps the train sign, and the validation t-stat clears the bar; the test period is reported and gates only once it holds 40 independent observations. A validation count below 30 is insufficient and re-queued, not closed. This is a confirmation under RESEARCH_SWEEP.md section 5, not a new backlog item.

"""


def main():
    current = LOG.read_text()
    marker = "confirm tsi z_90 below 5, ETH 1-day return"
    if marker in current:
        raise SystemExit("pre-registration already present")
    LOG.write_text(current + TEXT)
    print(f"appended, lines now {LOG.read_text().count(chr(10))}")


if __name__ == "__main__":
    main()
