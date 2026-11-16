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

## Added 2026-11-16

The queue had fallen to one item, and that item needs a pull, so two candidates were added from series already on disk. Neither is tested in this run. btc_volume_down_day_share_bottom, which was already in the queue, cannot be scored: the market panel has no volume column, and the only BTC volume series on disk starts 2022-10-06, which leaves the train period short. It stays queued and is marked blocked on data.

9. btc_funding_gap_bottom. Score 15 (prior 4, data 5, novelty 3, reach 2, cost 1).
Hypothesis: BTC funding running hot against ETH funding marks leverage concentrated in BTC, and that crowding precedes a bottom in BTC rather than a top, because the positioning family already failed on the top label. This is the change of the gap, not the level, which is what was rejected before. Rule: the factor is the 7-day change in the BTC minus ETH funding gap, lagged one bar, and the extreme is at or above its own trailing one-year 90th percentile, with neighbours at the 85th and the 95th. The label is the amended bottom event. Horizon: 30 days. Pass: the same bar as item 1 of the 2026-11-05 list. Expected independent n: about 30 to 50 episodes on BTC, which is thin. Assets: BTC, and ETH as the second asset.

10. eth_drawdown_90_bottom. Score 14 (prior 3, data 5, novelty 4, reach 1, cost 1).
Hypothesis: the BTC drawdown cell was insufficient at 10 fires, and the same measure on ETH may have enough episodes to be scored, which the BTC cell never reached. Rule: the close divided by the trailing 90-day high, lagged one bar, at or below its own trailing one-year 10th percentile, neighbours at the 5th and the 15th. The label is the amended bottom event. Horizon: 30 days. Pass: the same bar as item 1. Expected independent n: about 30 to 50 episodes on ETH. This extends the 2026-11-16 btc_drawdown_90_bottom verdict, which was insufficient, not a rejection, and it changes the asset.

## Added 2026-11-16, second pass

The queue had fallen to one scoreable item after btc_funding_gap_bottom was scored. stablecoin_supply_30d_bottom still needs a pull, and a research run never pulls. Both candidates below use series already in data/panel.csv and neither is tested in this run.

11. btc_basis_gap_chg7_bottom. Score 14 (prior 3, data 5, novelty 4, reach 1, cost 1).
Hypothesis: the basis gap between BTC and ETH was rejected as a 10-day return spread, and the funding gap's level was rejected the same way, but the 7-day change of the basis gap has no verdict against the bottom event. A basis that widens in BTC while price sits near its lows is leverage arriving at a low, which is a different question from the return spread. Rule: the factor is the 7-day change in the BTC basis minus the ETH basis, lagged one bar, and the extreme is at or above its own trailing one-year 90th percentile, neighbours at the 85th and the 95th. The label is the amended bottom event. Horizon: 30 days. Pass: the same bar as item 1 of the 2026-11-05 list. Expected independent n: about 30 to 50 episodes on BTC, which is thin. Assets: BTC, and ETH as the second asset. This extends the 2026-11-01 retest of basis_gap_btc_eth, which was rejected on the 10-day return, by changing the transform and the target.

12. eth_btc_ratio_z90_bottom. Score 13 (prior 3, data 5, novelty 3, reach 1, cost 1).
Hypothesis: ETH weakening against BTC marks a risk-off tape, and that weakness at a BTC low should precede a bottom if the rotation story is real. The ratio's 90-day z-score is already built in regime_tester/factors.py and has no verdict against the bottom event. Rule: the ETH close divided by the BTC close, its trailing 90-day z-score lagged one bar, at or below its own trailing one-year 10th percentile, neighbours at the 5th and the 15th. The label is the amended bottom event. Horizon: 30 days. Pass: the same bar as item 1. Expected independent n: about 30 to 50 episodes on BTC, which is thin. Assets: BTC, and ETH as the second asset.


## Added 2026-11-16, third pass

The queue had fallen to two scoreable items after btc_basis_gap_chg7_bottom was scored. stablecoin_supply_30d_bottom and btc_oi_share_chg7_top both wait on data, and a research run never pulls. Neither candidate below is tested in this run.

13. btc_vol_change_7d_bottom. Score 13 (prior 3, data 5, novelty 3, reach 1, cost 1).
Hypothesis: the level of realized vol was insufficient against the top event, and a falling vol after a spike is the capitulation shape, which is a different transform and a different target. Rule: the 7-day percent change in BTC 14-day realized vol, lagged one bar, at or below its own trailing one-year 10th percentile, neighbours at the 5th and the 15th. The label is the amended bottom event. Horizon: 30 days. Pass: the same bar as item 1 of the 2026-11-05 list. Expected independent n: about 30 to 50 episodes on BTC, which is thin. Assets: BTC, and ETH as the second asset. This extends the 2026-11-16 btc_realized_vol_percentile_top verdict, which was insufficient, not a rejection, by changing the transform and the target.

14. btc_oi_share_chg7_top. Score 12 (prior 3, data 2, novelty 4, reach 2, cost 1).
Hypothesis: BTC taking a rising share of open interest marks leverage concentrating in the leader, which should precede a top rather than a bottom. The level of the share has no verdict, and the change is the transform that has not been tried. Rule: the 7-day change in btc_oi_share, lagged one bar, at or above its own trailing one-year 90th percentile, neighbours at the 85th and the 95th. The label is the amended top event. Horizon: 30 days. Pass: the same bar as item 1. Expected independent n: about 20 episodes, below 40, because the series starts 2022-09-09 and the train period is short. Marked insufficient by design and blocked on data until the series is longer or the universe is pooled.
