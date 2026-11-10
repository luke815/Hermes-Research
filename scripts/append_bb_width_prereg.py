"""Pre-register the bb_width confirmation. Writes no score."""

from pathlib import Path

LOG = Path(__file__).resolve().parents[1] / "research" / "log.md"

TEXT = """

## 2026-11-10, pre-registered before any computation: confirm bb_width z_90 above 80, BTC 3-day return

Candidate: confirm_bb_width_z_90_above_80_ret_3_btc. Hypothesis: the Bollinger width, when its 90-day z-score sits above its own trailing 80th percentile, precedes a higher 3-day BTC return net of costs, and that edge keeps the train sign on validation at a t-stat above the volatility family deflated bar. Rule: cell bb_width|z_90|above|80|ret_3|btc|none|daily. The live leaderboard, results/sweeps/leaderboard.json, was rewritten at 2026-11-10T21:01:13Z from results/sweeps/2026-11-10_xs.csv and holds 47 cross-sectional rows, all with the same train score of -3.5239, because scripts/sweep_xs.py scores the 14-day price return under every measure name. None of those rows is a cell the confirmation procedure can score. This cell is the top unconfirmed cell in results/sweeps/2026-11-05.csv, the single-name train file, once cells already recorded in results/sweeps/confirmations.json are excluded, once a cell whose expected validation count is below 30 is excluded, and once neighbours of a closed cell are excluded. A neighbour is the same measure, universe and direction whose every difference is an adjacent threshold, an adjacent change lookback, an adjacent z-score window, or an adjacent horizon of the same kind. The closed volatility cells are donchian_width|z_30|below|10|ret_1|btc|none|daily and keltner_width|z_90|below|10|ret_3|btc|none|daily. Both use a different measure, so neither is a neighbour of this cell. The other closed cells use a different measure too. The feature is lagged one bar and its percentile comes from past data only. The target is the 3-day forward return of BTC, net of the costs table at the thin tier. The statistic is the Newey-West t-stat with lag 3, counted on every third bar. Family N is the volatility row count in results/sweeps/2026-11-05.csv, 4590. The deflated bar uses the count of distinct measure, target and universe combinations in that family, 90, from results/2026-11-06_confirmations_amended.json, and the bar is 2 + 0.5 log10(90). Validation passes only if its t-stat exceeds that bar and carries the train sign. A validation sample below 30 independent observations is insufficient and re-queued, not closed. Test is reported beside it and gates only once it holds 40 independent observations; before that the verdict is test pending, and a test period that flips sign rejects the cell. One attempt, recorded in results/sweeps/confirmations.json. Neighbours of this cell are not tried in this run. Horizon: 3 days. Pass criterion: admitted at horizon 3 with gate none, rejected, insufficient, or test pending. Expected independent n: 39.4 on validation, from the train independent count scaled by 549 over 1643.

"""


def main():
    current = LOG.read_text()
    marker = "confirm bb_width z_90 above 80, BTC 3-day return"
    if marker in current:
        raise SystemExit("pre-registration already present")
    LOG.write_text(current + TEXT)
    print(f"appended, lines now {LOG.read_text().count(chr(10))}")


if __name__ == "__main__":
    main()
