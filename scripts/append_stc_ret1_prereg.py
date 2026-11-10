"""Pre-register the stc ret_1 confirmation. Writes no score."""

from pathlib import Path

LOG = Path(__file__).resolve().parents[1] / "research" / "log.md"

TEXT = """

## 2026-11-10, pre-registered before any computation: confirm stc chg_7 above 80, ETH 1-day return

Candidate: confirm_stc_chg_7_above_80_ret_1_eth. Hypothesis: the 7-day change in the Schaff trend cycle, when it sits above its own trailing 80th percentile, precedes a lower 1-day ETH return net of costs, and that edge keeps the train sign on validation at a t-stat above the trend family deflated bar. Rule: cell stc|chg_7|above|80|ret_1|eth|none|daily. The live leaderboard, results/sweeps/leaderboard.json, was rewritten at 2026-11-10T19:01:13Z from results/sweeps/2026-11-10_xs.csv and holds 47 cross-sectional rows, all with the same train score of -3.5239, because scripts/sweep_xs.py scores the 14-day price return under every measure name. None of those rows is a cell the confirmation procedure can score. This cell is the top unconfirmed cell in results/sweeps/2026-11-05.csv, the single-name train file, once cells already recorded in results/sweeps/confirmations.json are excluded, once a cell whose expected validation count is below 30 is excluded, and once neighbours of a closed cell are excluded. A neighbour is the same measure, universe and direction whose every difference is an adjacent threshold, an adjacent change lookback, an adjacent z-score window, or an adjacent horizon of the same kind. The closed cell stc|chg_7|above|80|rel_3|eth|none|daily uses the same measure, universe and direction, but its target differs by kind: rel is not ret, so this cell is not a neighbour of it. The cell stc|chg_7|above|80|rel_1|eth|none|daily is a neighbour of that closed cell and is skipped. The other closed cells use a different measure. The feature is lagged one bar and its percentile comes from past data only. The target is the 1-day forward return of ETH, net of the costs table at the thin tier. The statistic is the Newey-West t-stat with lag 1, counted on every bar. Family N is the trend row count in results/sweeps/2026-11-05.csv, 16848. The deflated bar uses the count of distinct measure, target and universe combinations in that family, 324, from results/2026-11-06_confirmations_amended.json, and the bar is 2 + 0.5 log10(324). Validation passes only if its t-stat exceeds that bar and carries the train sign. A validation sample below 30 independent observations is insufficient and re-queued, not closed. Test is reported and gates admission only once it holds 40 independent observations. Horizon: 1 day. Pass criterion: validation Newey-West t-stat above the trend family deflated bar with the train sign, and test keeping that sign. Expected independent validation n is 105.6, from the train count scaled by 549 over 1643.

"""


def main():
    current = LOG.read_text()
    marker = "confirm stc chg_7 above 80, ETH 1-day return"
    if marker in current:
        raise SystemExit("pre-registration already present")
    LOG.write_text(current + TEXT)
    print(f"appended, lines now {LOG.read_text().count(chr(10))}")


if __name__ == "__main__":
    main()
