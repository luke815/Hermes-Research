# Generated candidates

Produced 2026-11-05 because the queue had five items, below the eight-item floor in section 2 of the research loop. Scored 0 to 5 on prior, data, novelty, reach and cost. Nothing here is tested in this run. Each candidate states its hypothesis, rule, horizon, pass criterion and expected independent n.

Rejected cells already in the log are not regenerated. The options family, Fear and Greed, basket funding z-score, liquidations and the long/short ratio all have verdicts, so none of them reappears under the same transform and target.

## Ranked

1. btc_funding_persistence_top. Score 19 (prior 5, data 4, novelty 4, reach 4, cost 2).
Hypothesis: a run of days with BTC funding above its own trailing 80th percentile marks crowding that precedes a damaging drawdown, and persistence is a different signal from the level percentile already rejected. Rule: the factor is the count of consecutive days, ending yesterday, on which the BTC 7-day average funding sat above its own trailing one-year 80th percentile. The extreme is a streak of 5 or more days, with neighbours of 3 and 7. The label is the amended top event: candidate days within 5 percent of the 60-day high, and a top is a 20 percent drop within 30 days. Horizon: 30 days. Pass: lift above 1 in validation with the episode-bootstrap 90 percent interval clear of 1, the train sign agrees, and at least 30 episodes across train and validation. Expected independent n: about 40 to 60 episodes on BTC since 2021, more once pooled. Depends on the C1 rerun for the labels.

2. btc_drawdown_90_bottom. Score 18 (prior 4, data 5, novelty 4, reach 3, cost 2).
Hypothesis: a deep drawdown from the 90-day high precedes a durable low, because capitulation clusters at lows and the price structure is already on disk. Rule: the factor is the close divided by the trailing 90-day high, lagged one bar, and the extreme is at or below the trailing one-year 10th percentile, with neighbours at the 5th and 15th. The label is the amended bottom event: candidate days within 5 percent of the 60-day low, and a bottom is a 20 percent rise within 30 days without a 7 percent dip. Horizon: 30 days. Pass: the same bar as item 1. Expected independent n: about 30 to 50 episodes on BTC. Depends on the C1 rerun.

3. btc_realized_vol_percentile_top. Score 17 (prior 4, data 5, novelty 3, reach 3, cost 2).
Hypothesis: realized volatility at its own trailing extreme precedes tops, because blow-off moves arrive with a vol spike, and the vol factor already in the score was tested against the 10-day return, not against the top event. Rule: 30-day realized vol, lagged one bar, at or above its trailing one-year 90th percentile, neighbours at the 85th and 95th. Label: the amended top event. Horizon: 30 days. Pass: the same bar as item 1. Expected independent n: about 30 to 50 episodes on BTC. Depends on the C1 rerun.

4. eth_btc_30d_conditioning. Score 16 (prior 4, data 5, novelty 4, reach 2, cost 1).
Hypothesis: the admitted momentum factor's edge is conditional on ETH outperforming or underperforming BTC, so the same factor should be reported inside terciles of the ETH/BTC 30-day return rather than pooled. Rule: split the existing btc_ret_30 quintile spread by the tercile of the ETH/BTC trailing 30-day return, lagged one bar, and compare the spread inside each tercile against the unsplit spread. Horizon: 10 days, non-overlapping. Pass: the spread keeps its sign in validation and test inside at least one tercile, and that tercile's spread exceeds the unsplit spread in both. Expected independent n: about 20 per tercile per period, which is thin, so a cell under 30 observations is reported and not quoted.

5. stablecoin_supply_30d_bottom. Score 15 (prior 4, data 1, novelty 5, reach 4, cost 1).
Hypothesis: a rising stablecoin supply is dry powder and should precede bottoms, and no verdict exists for it because the series is not on disk. Rule: 30-day percent change in total stablecoin supply from DefiLlama, lagged one bar, at or above its trailing one-year 90th percentile. Label: the amended bottom event. Horizon: 30 days. Pass: the same bar as item 1, after a reachability check and a verify_panel pass on the series. Expected independent n: about 30 episodes. This is a D6 item in disguise and should be pulled before it is tested.

6. btc_volume_down_day_share_bottom. Score 14 (prior 3, data 5, novelty 3, reach 2, cost 1).
Hypothesis: a run of down days on rising volume marks capitulation and precedes a bottom. Rule: the share of the last 7 days that closed down and had volume above their own trailing 30-day median, lagged one bar, extreme at or above the trailing one-year 90th percentile. Label: the amended bottom event. Horizon: 30 days. Pass: the same bar as item 1. Expected independent n: about 30 to 50 episodes.

## Disproof, this week's pair

7. disproof_btc_ret_30_weekly. Score 13 (prior 3, data 5, novelty 3, reach 2, cost 0).
Hypothesis: the admitted momentum factor is an artifact of the daily horizon, and it should lose its sign on weekly bars. Rule: the same quintile spread as the weekly retest, on weekly closes, horizon 2 weeks, non-overlapping by construction. Pass for the factor: the sign holds in both halves. A flip demotes it. Expected independent n: about 25 per half, below 40, so the result is reported as thin either way.

8. disproof_eth_funding_second_asset. Score 12 (prior 3, data 4, novelty 2, reach 2, cost 1).
Hypothesis: the ETH funding factor in the score is an ETH-specific artifact and should flip on SOL. Rule: the same 30-day z-score quintile spread, horizon 10 days, non-overlapping, on SOL instead of ETH. Pass for the factor: the sign holds in both halves on SOL. Expected independent n: about 40 per half where SOL history exists.

## Not generated, and why

- Anything in the options family, Fear and Greed, basket funding, liquidations or the long/short ratio. Each has a verdict and would need a new transform or target, which the candidates above already change where they touch the same family.
- A cross-sectional candidate on the full universe. D1 is not finished, and a candidate that needs it would score low on data and cost.
