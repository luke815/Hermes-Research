# Research backlog

Ordered by the research program, section 9. One item at a time, pre-registered before any number is computed, verdict before the next item starts.

## Queue

Revised by research/RESEARCH_LOOP.md section 8. D1 comes before everything else because every cross-sectional item depends on it.

1. D1, continued. Binance, Bybit and OKX symbol lists are recorded, not admitted. Binance: 923 USDT perps, 31 stopped before 2026-10-19, in data/binance_span.csv. Those 31 now have daily prices in data/binance_prices/ (22,653 rows) and daily funding in data/binance_funding/ (25,045 days, verdict 2026-11-03, every file matching the archive listing). Bybit: 1,136 USDT folders, 309 stopped, in data/bybit_span.csv. OKX: 672 USDT swaps, 154 stopped, in data/okx_span.csv. What remains is open interest and the long/short ratio for the 31 Binance stopped names (the metrics archive is daily only, one file per day, and it runs past the last trade, so it needs its own run), liquidations (the archive publishes none), and the six-series history for the live names and for Bybit and OKX. Do not rerun any span pull, the Binance price pull or the Binance funding pull; each resumes from its saved files.
2. C1 rerun on the amended targets. Top candidates are days within 5 percent of the 60-day high; a top is a 20 percent drop within 30 days. Bottom candidates are days within 5 percent of the 60-day low; a bottom is a 20 percent rise within 30 days without a 7 percent dip. Base rates among candidate days, not all days.
3. C2 rerun on the amended labels. The ETH funding cell is a live candidate under the amended bar.
4. C3 to C7 as parallel subagents: TD Sequential, trend exhaustion, options, breadth, on-chain and flows.
5. D2, D4, D6, D7 between cycle items. Then C8, C9, and the cross-sectional items.

Completed, with verdicts in research/log.md: point-in-time universe (insufficient, 2026-10-30), costs table (admitted, 2026-10-31), three-period split (rejected, 2026-11-01), C1 on the old labels (recorded, too loose), C2 on the old labels (rejected).

Cycle layer remaining, scored on episodes:

1. Point-in-time universe and per-asset daily panel, with first-date inventory. Verdict 2026-10-30: insufficient. Neither source can state both the rule and the name list for the same date. See research/log.md. Do not rerun until a source lists the names that existed on a past date.
2. Costs table and net-return plumbing. Verdict 2026-10-31: admitted at horizons 1, 3 and 10 with gate none. regime_tester/costs.py, results/2026-10-31_costs.json. The panel has no USD open interest, so every row takes the thin tier until the per-asset panel exists.
3. Three-period split and per-year reporting in the tester. Verdict 2026-11-01: rejected because no factor keeps its sign at a usable size in both validation and test. regime_tester/periods.py, results/2026-11-01_three_period.json. The score is unchanged. The weekly retest of the three removed factors was run the same day and all three stay out: basis_btc_z30 points the wrong way on BTC, basis_gap_btc_eth keeps its sign but is too thin and shrinks the alt gap, dispersion_14 flips. results/2026-11-01_retest.json.

Cycle layer, from research/RESEARCH_PROGRAM_CYCLE.md. These come before the cross-sectional items because the targets and the episode counter are shared. One per night. Detectors are scored on episodes, never on days.

- C1. Targets and episode counter. Verdict 2026-11-01: recorded, not admitted. The primary definitions are too loose: T(30, 15%) is true on 500 of 2,496 BTC days, 61 episodes, and B(30, 15%, 7%) is 72. The program expected 15 to 25. Only T(60, 25%) is near that, at 26, with none in 2023 or 2024. results/2026-11-01_weekly.json. Do not score a detector on these labels until the thresholds are tightened and pre-registered.
- C2. Positioning family, single-factor event tests, daily. Verdict 2026-11-02: rejected because no factor keeps a lift above 1 in both validation and test on BTC and on the pooled names. The label was tightened to T(60, 25%) and B(60, 30%, 10%) before scoring. results/2026-11-02_positioning.json.
- C3. TD Sequential, daily and weekly, setups and countdowns, as events. Report lead time and false-alarm rate with the lift.
- C4. Trend exhaustion family: Mayer multiple, Pi cycle, RSI and divergences, parabolic extension, weekly band.
- C5. Options family: DVOL, skew, risk reversal, implied minus realized vol.
- C6. Breadth family on the 2022-09 universe.
- C7. On-chain, sentiment and flows. Check which sources are reachable first, then test only those.
- C8. Scorecards for top and bottom from everything admitted. Calibration table, analogs, and write the cycle key.
- C9. Risk-off ladder backtest and the per-year table.
- C10. Weekly cycle layer, with its sample size stated plainly.

Then the cross-sectional items resume.

4. Single-feature cross-sectional tests: relative strength at 14 and 30 days.
5. Funding 7-day average and open-interest 7-day change as cross-sectional signals.
6. One-day reversal in the bottom half of the universe by open interest.
7. Composite ranking, equal weights, decile and information-coefficient report, by year and by heat tercile.
8. Setups, in order: crowded long, compression breakout, breakdown, momentum pullback, then capitulation reversal, exhaustion, failed breakout, short squeeze.
9. Regime gate test for every admitted setup, with and without the gate.
10. Four-hour panel for the top 30 by open interest, and the 1 to 3 day versions of the capitulation and short-squeeze setups.
11. Cross-venue and Hyperliquid funding divergence as a confirmation feature.
12. Learned weights for the composite by rolling walk-forward, against equal weights.

## Pass rules

Sign and rough size must hold in validation and in test, not only in train. Report per calendar year. Every return is net of the costs table. Fewer than 40 independent triggers is insufficient, not promising. An edge that exists at one threshold and vanishes at its neighbours is noise. With more than 20 tests since the last admission, the required t-stat rises to 3.

## Blocked

Market-wide open-interest dominance and the put/call ratio need get_market_positioning_history, which returns a server error. One attempt per week. Gamma exposure history is broken by a methodology change on 2026-06-01.

## Previously rejected

Raw funding level, OI spread, BTC dominance, liquidations, long/short ratios, breadth, speculation, volume participation, OI momentum, skew, risk reversal, vol premium, DVOL, options term structure, basket funding z-score, Fear and Greed. Do not retest without a new transform or horizon. Details in log.md.
