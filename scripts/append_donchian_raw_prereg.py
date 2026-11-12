"""Append the Donchian-width pre-registration. Writes no computed number."""

from pathlib import Path

TEXT = """

## 2026-11-12, pre-registered before any computation: confirm donchian_width raw below 20, BTC 1-day return

Candidate: confirm_donchian_width_raw_below_20_ret_1_btc. Hypothesis: the Donchian channel width, when it sits below its own trailing 20th percentile, precedes a lower 1-day BTC return net of costs, and that edge keeps the train sign on validation at a t-stat above the volatility family deflated bar. Rule: cell donchian_width|raw|below|20|ret_1|btc|none|daily. The live leaderboard, results/sweeps/leaderboard.json, was rewritten at 2026-11-12T13:01:13Z from results/sweeps/2026-11-12_xs.csv and its top row is breadth|xs_rank|above|90|rel_1|pit_cross_section|none|daily, a cross-sectional cell the confirmation procedure cannot score. This cell is the top unconfirmed cell in results/sweeps/2026-11-05.csv, the single-name train file, once cells already recorded in results/sweeps/confirmations.json are excluded, once a cell whose expected validation count is below 30 is excluded, and once neighbours of a closed cell are excluded. A neighbour is the same measure, universe and direction whose every difference is an adjacent threshold, an adjacent change lookback, an adjacent z-score window, or an adjacent horizon of the same kind. The one recorded donchian_width cell is donchian_width|z_30|below|10|ret_1|btc|none|daily, which is closed. Its transform is a 30-bar z-score rather than the raw level, so the transform difference is not an adjacent z-score window and the neighbour rule does not connect it. The neighbour check lists 0 neighbour hits. Twenty-seven cells rank above this one and each is already attempted, a neighbour of a closed cell, or expects fewer than 30 independent validation observations. The feature is lagged one bar and its percentile comes from past data only. The target is the 1-day forward return of BTC, net of the costs table at the thin tier. The statistic is the Newey-West t-stat with lag 1, counted on every bar. Family N is the volatility row count in results/sweeps/2026-11-05.csv, 4590, from the output of scripts/pick_from_trainfile.py written today. The deflated bar uses the count of distinct measure, target and universe combinations in that family, 90, from the same output and from results/2026-11-06_confirmations_amended.json, and the bar is 2 + 0.5 log10(90). Validation is 2024-07-01 to 2025-12-31 and test is 2026-01-01 onward. Pass: validation independent n at least 30, the validation spread keeps the train sign, and the validation t-stat clears the bar. The test period is reported beside it and gates only once it holds 40 independent observations; before that a validation pass is test pending, and a test period that flips the sign rejects the cell. A validation sample below 30 is insufficient and re-queued, not closed. One attempt, recorded in results/sweeps/confirmations.json.

"""

path = Path("research/log.md")
text = path.read_text()
if "confirm donchian_width raw below 20" in text:
    raise SystemExit("already pre-registered")
path.write_text(text + TEXT)
print("appended", path.stat().st_size)
