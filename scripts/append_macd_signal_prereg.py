"""Pre-register the macd_signal confirmation. Writes no score."""

from pathlib import Path

LOG = Path(__file__).resolve().parents[1] / "research" / "log.md"

TEXT = """

## 2026-11-10, pre-registered before any computation: confirm macd_signal raw below 20, ETH 3-day relative return

Candidate: confirm_macd_signal_raw_below_20_rel_3_eth. Hypothesis: the MACD signal line, when it sits below its own trailing 20th percentile, precedes a lower 3-day ETH return relative to BTC net of costs, and that edge keeps the train sign on validation at a t-stat above the trend family deflated bar. Rule: cell macd_signal|raw|below|20|rel_3|eth|none|daily. The live leaderboard, results/sweeps/leaderboard.json, was rewritten at 2026-11-10T23:00:00Z from results/sweeps/2026-11-10_xs.csv and its top row is breadth|xs_rank|above|90|rel_1|pit_cross_section|none|daily, a cross-sectional cell the confirmation procedure cannot score. This cell is the top unconfirmed cell in results/sweeps/2026-11-05.csv, the single-name train file, once cells already recorded in results/sweeps/confirmations.json are excluded, once a cell whose expected validation count is below 30 is excluded, and once neighbours of a closed cell are excluded. A neighbour is the same measure, universe and direction whose every difference is an adjacent threshold, an adjacent change lookback, an adjacent z-score window, or an adjacent horizon of the same kind. No closed cell uses the macd_signal measure, so none is a neighbour of this cell. The feature is lagged one bar and its percentile comes from past data only. The target is the 3-day forward return of ETH minus the 3-day forward return of BTC, both net of the costs table at the thin tier. The statistic is the Newey-West t-stat with lag 3, counted on every third bar. Family N is the trend row count in results/sweeps/2026-11-05.csv, 16848. The deflated bar uses the count of distinct measure, target and universe combinations in that family, 324, from results/2026-11-06_confirmations_amended.json, and the bar is 2 + 0.5 log10(324). Validation is 2024-07-01 to 2025-12-31 and test is 2026-01-01 onward. Pass: validation independent n at least 30, the validation spread keeps the train sign, and the validation t-stat clears the bar; the test period is reported and gates only once it holds 40 independent observations. Fewer than 30 independent observations in validation is insufficient and re-queued, not closed. One attempt, ever.

"""


def main():
    current = LOG.read_text()
    marker = "confirm macd_signal raw below 20, ETH 3-day relative return"
    if marker in current:
        raise SystemExit("pre-registration already present")
    LOG.write_text(current + TEXT)
    print(f"appended, lines now {LOG.read_text().count(chr(10))}")


if __name__ == "__main__":
    main()
