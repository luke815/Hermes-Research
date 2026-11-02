# Research log

Each round: date, candidate, transform, horizon, in-sample, out-of-sample, correlation with existing factors, decision, reason.

The record below covers work done before this log existed, reconstructed from the session. Figures are the ones reported at the time.

## 2026-10-19 to 2026-10-26, reconstructed

Admitted to the heat score, equal weight:

- btc_ret_30, btc_vol_z90, btc_trend_stretch, basis_btc_z30, eth_funding_z30. Each kept its sign on BTC and the alt basket across both halves. Horizon 10 days.
- basis_gap_btc_eth, direction -1. High reading preceded worse returns: -6.3% then -2.0% over 10 days. The only factor where high means caution.
- dispersion_14. Widened the out-of-sample alt-basket gap from 7.0% to 7.7%. Correlation with momentum 0.44.

Rejected:

- Breadth above the 50-day average. Correlation 0.66 with momentum. Adding it shrank the gap.
- Speculation, share of alts beating BTC over 90 days. Sign held, effect too small.
- Liquidations and long/short ratios, nine factors. One kept its sign, under 0.6% out of sample.
- OI momentum, total OI change, volume regime, volume confirmation. All flipped sign.
- Skew, BTC and ETH, 30-day and 90-day z-score. Sign held and direction was right, but correlation -0.62 with momentum. Adding it cut the gap from 7.0% to 6.0%.
- Risk reversal. Correlation 0.64 with momentum. Gap fell from 7.5% to 5.8%.
- Volatility risk premium. Correlation 0.34. Gap fell to 6.8%.
- DVOL, BTC and ETH. ETH DVOL correlated only 0.11 with momentum but still shrank the gap, 7.5% to 7.3%.
- Options term structure slope, 7-day versus 90-day. Flipped sign. Curvature kept its sign at 0.5% out of sample, too small.
- Basket funding z-score and the BTC/ETH/alt blend. Blend correlated 0.69 with ETH funding already in the score.
- Fear & Greed index, daily since 2018. Correlation 0.74 with momentum. Gap fell from 7.5% to 5.8%.

Model decisions:

- Learned static weights, fit once on the first half, correlated -0.007 out of sample against +0.13 for equal weights. Rejected. Overfit.
- Rolling two-year refit correlated +0.11 and ranked correctly: top fifth realized +3.3%, bottom fifth +1.0% over 10 days. Adopted as the pricing model. Levels are not reliable; the ranking is.

## 2026-10-27

TA library built in regime_tester/ta.py: moving-average distance and slope at 20/50/200, Donchian breakouts at 20 and 55, RSI, Bollinger width, ATR regime. Twelve candidates, horizon 10 days.

Five kept their sign on both BTC and the alt basket: slope_ma20, slope_ma50, dist_ma200, bollinger_width, atr_regime.

Incremental test against the live score, alt basket, out of sample: slope_ma20 widened the gap from 7.53% to 7.91%, atr_regime to 7.75%. The other three shrank it.

Decision: none admitted to the regime score. slope_ma20 correlates 0.83 with btc_ret_30, so the gain is duplicated momentum. atr_regime correlates 0.91 with btc_vol_z90, so it is a restatement of the volatility factor. Both are recorded as valid standalone signals for the scanner, not as score components.

## 2026-10-27, score reduced from seven factors to four

Rerun on the current panel, 2,491 rows ending 2026-10-26. Top minus bottom quintile, 10-day forward return, second half of the sample, n=245 both.

Three factors failed sign stability on the full history and were removed: basis_btc_z30 flipped on BTC, basis_gap_btc_eth flipped on the alt basket and shrank to -0.51% on BTC, dispersion_14 flipped on BTC. Figures in results/2026-10-27_retest.json.

Combined model, out of sample, from results/2026-10-27_drop.json:
- seven factors: BTC +2.30%, alt basket +6.91%
- four factors: BTC +2.66%, alt basket +6.43%

Dropping them improved BTC by 0.36 percentage points and cost 0.48 on the alt basket. The BTC gain is the one that counts, because that is where the sign flips were. The three stay in the weekly retest with n reported beside each, and return only if they pass on the full history.

The score is now a momentum and volatility read: btc_ret_30, btc_vol_z90, btc_trend_stretch, eth_funding_z30. It is not a broad regime model.

## 2026-10-27, cross-venue funding tested, not admitted

Rebuilt the funding factor from Laevitas OI-weighted funding across venues, 2,033 days from 2021-03-26 to 2026-10-26. It is not capped: zero days sit at the 0.01 Binance ceiling, against 784 of 2,472 for the Binance series.

30-day z-score, top minus bottom quintile, 10-day forward return, n=201 per half. BTC: train -0.18%, test +0.59%. Alt basket: train +1.53%, test +1.77%. The sign flips on BTC, so it fails admission. Correlation with eth_funding_z30 is 0.39, so it is not a duplicate, but a factor that points the wrong way on BTC in one half does not join. Stays in the weekly retest.

## 2026-10-27 17:21 UTC hourly

Heat -0.116 on 2026-10-26, mid zone, no 0.4 crossing. Tunnel HTTP 200. No qualifying setup. Results in results/2026-10-27_hourly.json.

## 2026-10-27 18:23 UTC hourly

Heat -0.116 on 2026-10-26, unchanged from the 17:21 run, mid zone, no 0.4 crossing. Tunnel HTTP 200. No qualifying setup. Results in results/2026-10-27_hourly.json.

## 2026-10-27 19:24 UTC hourly

Heat -0.116 on 2026-10-26, unchanged from the 18:23 run, mid zone, no 0.4 crossing. Tunnel HTTP 200. No qualifying setup. Results in results/2026-10-27_hourly.json.


## 2026-10-27 20:25 UTC hourly

Heat -0.116 on 2026-10-26, unchanged from the prior run, mid zone, no 0.4 crossing. Tunnel HTTP 200. No qualifying setup. Results in results/2026-10-27_hourly.json.

## 2026-10-27 21:26 UTC hourly

Heat -0.116 on 2026-10-26, unchanged from the 20:25 run, mid zone, no 0.4 crossing. Tunnel HTTP 200. No qualifying setup. Results in results/2026-10-27_hourly.json.

## 2026-10-27 22:27 UTC hourly

Heat -0.116 on 2026-10-26, unchanged from the 21:26 run, mid zone, no 0.4 crossing. Tunnel HTTP 200. No qualifying setup. Results in results/2026-10-27_hourly.json.

## 2026-10-27 23:27 UTC hourly

Heat -0.116 on 2026-10-26, unchanged from the 22:27 run, mid zone, no 0.4 crossing. Tunnel HTTP 200. No qualifying setup. Results in results/2026-10-27_hourly.json.

## 2026-10-28 01:29 UTC hourly

Heat -0.116 on 2026-10-26, unchanged from the 00:28 run, mid zone, no 0.4 crossing. Tunnel HTTP 200. No qualifying setup. Results in results/2026-10-28_hourly.json.

## 2026-10-28 03:31 UTC hourly

Heat -0.116 on 2026-10-26, unchanged from the 02:30 run, mid zone, no 0.4 crossing. Tunnel HTTP 200. No qualifying setup. Results in results/2026-10-28_hourly.json.

## 2026-10-28 06:32 UTC hourly

Panel bar rolled to 2026-10-27 (daily refresh 05:33 UTC). Heat -0.113, mid zone, no 0.4 crossing versus the prior bar or the 05:32 run. Tunnel HTTP 200. No qualifying setup. Results in results/2026-10-28_hourly.json.

## 2026-10-28 07:33 UTC hourly

Heat -0.113 on 2026-10-27, unchanged from the 06:32 run (delta 0), mid zone, no 0.4 crossing. Tunnel HTTP 200. No qualifying setup. Results in results/2026-10-28_hourly.json.

## 2026-10-28 08:34 UTC hourly

Heat -0.113 on 2026-10-27, unchanged from the 07:33 run (delta 0), mid zone, no 0.4 crossing. Tunnel HTTP 200. No qualifying setup. Results in results/2026-10-28_hourly.json.

## 2026-10-28 09:34 UTC hourly

Heat -0.113 on 2026-10-27, unchanged from the 08:34 run (delta 0), mid zone, no 0.4 crossing. Tunnel HTTP 200. No qualifying setup. Results in results/2026-10-28_hourly.json.

## 2026-10-28 11:35 UTC hourly

Heat -0.113 on 2026-10-27, unchanged from the 10:35 run (delta 0), mid zone, no 0.4 crossing. Tunnel HTTP 200. No qualifying setup. Results in results/2026-10-28_hourly.json.

## 2026-10-27, panel row count

The loader change that drops days missing price or funding removed 20 rows, not 19, and added nothing. The panel went from 2,492 rows ending 2026-10-27 to 2,472 rows. The 20 dates are 2020-01-01 through 2020-01-20. BTC price exists for all of them. BTC funding starts 2020-01-21, confirmed from the raw Coinalyze file, whose first bar is timestamp 1579564800. So the rows were removed because funding did not exist yet, not because of a data error. The earlier "2,491" figure was the panel before today's row was reconciled and is not the comparison to use.


## 2026-10-29, panel row count

Daily refresh added one row and removed none. The panel went from 2,472 rows ending 2026-10-27 to 2,473 rows ending 2026-10-28. The added date is 2026-10-28, the completed day pulled from Coinalyze (20 bars on each of the five series) and from Laevitas (one daily bar each for basis, OI-weighted funding, realized vol, DVOL, skew, ATM IV and risk reversal, BTC and ETH). verify_panel.py: PASS panel_end=2026-10-28 today=2026-10-29 age=1d rows=2473 trailing_blank_cols=0.

## 2026-10-29, code review fixes

1. The rolling pricing model trained on forward returns that were not yet known. The window for day i ended at i, but the return at i-1 uses prices through i+9. Purged the last 10 rows. After the fix the top-versus-bottom spread by year, non-overlapping, is negative in 2022 (-4.71%, n=33), 2023 (-0.82%, n=37) and 2026 (-4.52%, n=30), and positive only in 2024 (+2.47%, n=37) and 2025 (+0.87%, n=37). The ranking does not hold. The forecast pane note and the digest now say the number is context, not a forecast. results/2026-10-29_purge.json.

2. Every spread now carries an independent n and a non-overlapping t-stat. results/2026-10-29_independent.json. Only btc_ret_30 clears a t-stat of 2: +5.18% on BTC (t=2.26, n=24) and +9.59% on alts (t=2.72, n=24). The other three live factors are between t=0.27 and t=1.98.

3. Hot zone by year, non-overlapping: overall +2.07% on 23 independent observations. 2020 +7.91% (n=5), 2021 +1.13% (n=4), 2023 +1.24% (n=7), 2024 +4.01% (n=4). The average is carried by 2020 and 2024. results/2026-10-29_hotzone.json.

4. Every alt spread above is survivor-biased. The basket is the 20 names chosen today, applied to the whole history. It stays labelled that way until the point-in-time universe exists.

5. test_factors now uses expanding cut-offs, so each bar is judged against the distribution strictly before it.

6. The live score is four factors, not three. Recomputed: BTC +2.90% (t=1.39, n=25), alts +3.98% (t=1.24, n=25). Neither is distinguishable from noise. results/2026-10-29_four.json.

7. The hardcoded timestamp in clean_overlap is gone. It now drops duplicate dates, whatever they are.

8. Added ForecastIgnoresFuture, which triples every price after day t and asserts the forecast at t does not move. It passes. It would have failed before the purge.

## 2026-10-30, pre-registered before any computation: point-in-time universe

Candidate: pit_universe. Hypothesis: a name can be scored on a date only if it had already met a liquidity threshold on that date, so the 20 names chosen today are not applied to 2021. Rule: a name is a member on date t when the prior completed daily bar (shift one) shows open interest of at least 20,000,000 USD or volume of at least 10,000,000 USD on Binance, Bybit or OKX, taking the maximum across those venues so a name listed on more than one is not counted twice. Hyperliquid is out: its retained history starts in 2025 and cannot cover the train period. Horizon: none. This item builds the universe the later tests score against; it does not score a return. Pass: the panel exists, verify_panel.py passes, membership uses only data known on the date, and the survivorship check is reported. That check compares, at 2021-06-30, 2022-06-30, 2023-06-30, 2024-06-30 and 2025-06-30, the count of names in the point-in-time universe with the count of the fixed 20 that would have qualified. The fixed 20 overstating the universe at any of those dates is the bias this item exists to remove, and that is a pass, not a failure. Fail: the panel cannot be built from retained history, or membership depends on a future bar. Neighbour check, reported not gated: the same count at 10,000,000 and 40,000,000 USD open interest, and at 5,000,000 and 20,000,000 USD volume.

Verdict: insufficient. No source states both the membership rule and the name list for the same date. Laevitas retained history has USD open interest and volume from 2021-03-26 (460 daily bars for Binance BTCUSDT, 2021-03-26 to 2022-06-30, saved to data/raw/_parts/probe_binance_BTCUSDT.json) but every discovery route requires a currency already known, and no endpoint lists the names that existed on a past date. The current Binance catalog has 588 names and the 2026-10-29 snapshot 820, neither of which is a historical list. Coinalyze lists names but its open interest starts 2022-09-19 on Binance, Bybit and OKX, and its market list is today's listings. Of the fixed 20, zero have an open-interest bar on 2021-06-30 or 2022-06-30. The survivorship comparison was not computed, because the point-in-time count cannot be built. results/2026-10-30_pit_universe.json.

## 2026-10-31, pre-registered before any computation: costs table and net-return plumbing

Candidate: costs. Hypothesis: a backtest return overstates the tradeable result by the taker fee, the slippage and the funding carry paid while the position is held, so every later test needs one function that subtracts all three and a table that states the rates. Rule: taker fee 5 bps per side, so 10 bps round trip, on every venue. Slippage 10 bps per side for a name whose open interest is at or above 50,000,000 USD, and 25 bps per side below that, judged on the open interest known at entry (shifted one bar). Funding carry is the realized funding over the holding window, summed in the position's direction: a long pays positive funding. The Coinalyze funding close is a percent per 8-hour settlement, so the daily carry in return units is the close divided by 100, accrued once per day. No funding series means the carry term is missing and the result says so, never zero. Horizon: 1, 3 and 10 days, the three horizons in section 3. Pass: the table is on disk, the function returns gross beside net, a long and a short on the same window pay opposite carry, and perturbing every price and every funding print after the close of the window leaves the cost computed at t unchanged. Fail: the carry sign is wrong, or the cost at t depends on a bar after its window has closed. This item builds the plumbing. It does not score a signal, so there is no edge to admit.

Verdict: admitted at horizons 1, 3 and 10 with gate none. Plumbing, not a signal. regime_tester/costs.py holds the table and apply_costs, which returns gross beside net. Tests in tests/test_regime_tester.py cover the carry sign, the thin tier, a missing funding series, and the no-look-ahead check; 13 tests, all passing. Worked example on BTC, long, thin tier because the panel has no USD open interest, from results/2026-10-31_costs.json: at 10 days the mean gross is 1.4044 percent and the mean net is 0.6935 percent, a gap of 0.7109 percentage points on 2,464 closed windows, of which 0.6 is the round trip and 0.1109 is the mean carry. The same file has the 1-day and 3-day rows.

## 2026-10-30, panel row count

Daily refresh added one row and removed none. The panel went from 2,473 rows ending 2026-10-28 to 2,474 rows ending 2026-10-29. The added date is 2026-10-29, the completed day pulled from Coinalyze (20 bars on each of the five series) and from Laevitas (one daily bar each for basis, OI-weighted funding, realized vol, DVOL, skew, ATM IV and risk reversal, BTC and ETH). verify_panel.py: PASS panel_end=2026-10-29 today=2026-10-30 age=1d rows=2474 trailing_blank_cols=0.

## 2026-11-01, pre-registered before any computation: three-period split and the four regime factors

Candidate: three_period. Hypothesis: the half-sample split hides whether a factor's edge survives the two periods that were never used to choose it, so the four factors still in the heat score must be scored again on the three fixed periods before any later test trusts them. Rule: top quintile minus bottom quintile of the factor, cut-offs from the expanding distribution of values strictly before the bar. Factors are the four live ones, taken as they are built: btc_ret_30, btc_vol_z90, btc_trend_stretch, eth_funding_z30, each already a trailing z-score shifted one bar. Direction is the sign already in the score, +1 for all four, so a positive spread is the claim. Assets: BTC and the equal-weight alt basket, reported side by side, with the basket labelled survivor-biased because the point-in-time universe does not exist. Horizons: 1, 3 and 10 days, side by side. Returns are net of the costs table, long both quintiles, thin tier, because the panel has no USD open interest; gross is reported beside net once per horizon. Periods, fixed and not moved: train to 2024-06-30, validation 2024-07-01 to 2025-12-31, test from 2026-01-01. t-stats use non-overlapping windows, every h-th bar. Per calendar year, with the independent count per year. Neighbour check: the same spread at the 75th and 85th percentile cuts, reported next to the 80th. Pass: the spread keeps its sign and a rough size in validation and in test, the non-overlapping t-stat is at least 2, the sign holds in more than one calendar year, and the neighbour cuts do not flip it. With more than 20 tests since the last admission the bar rises to 3. Fail: the sign flips in validation or in test, the edge sits in one calendar year, or it exists at the 80th and vanishes at the 75th and 85th. Fewer than 40 independent triggers is insufficient, not a rejection. This item does not change the score. A factor that fails here is reported as failing, and removal waits for the weekly retest.

Verdict: rejected because no factor keeps its sign at a usable size in both validation and test. The only cell with 40 or more independent observations in both held-out periods is btc_ret_30 on the alt basket at 1 day: validation +0.7447 percent (t=1.1389, n=79), test +0.2831 percent (t=0.4333, n=56), from results/2026-11-01_three_period.json. The sign holds and the 75th and 85th cuts hold, but neither t-stat clears 2 and the test spread is under half the validation spread. At 10 days every factor has independent n below 40 in both validation and test, so that horizon is insufficient rather than a measured edge. The score is unchanged. One test since the last admission, so the t-stat bar stayed at 2. regime_tester/periods.py, 16 tests passing.

## 2026-10-31, panel row count

Daily refresh added one row and removed none. The panel went from 2,474 rows ending 2026-10-29 to 2,475 rows ending 2026-10-30. The added date is 2026-10-30, the completed day pulled from Coinalyze (20 bars on each of the five series) and from Laevitas (one daily bar each for basis, OI-weighted funding, realized vol, DVOL, skew, ATM IV and risk reversal, BTC and ETH). verify_panel.py: PASS panel_end=2026-10-30 today=2026-10-31 age=1d rows=2475 trailing_blank_cols=0.

## 2026-11-01, panel row count

Daily refresh added one row and removed none. The panel went from 2,475 rows ending 2026-10-30 to 2,476 rows ending 2026-10-31. The added date is 2026-10-31, the completed day pulled from Coinalyze (20 bars on each of the five series) and from Laevitas (one daily bar each for basis, OI-weighted funding, realized vol, DVOL, skew, ATM IV and risk reversal, BTC and ETH). verify_panel.py: PASS panel_end=2026-10-31 today=2026-11-01 age=1d rows=2476 trailing_blank_cols=0 dupes=0 missing_days=0.

## 2026-11-01, pre-registered before any computation: episode targets

Candidate: episodes. Hypothesis: a detector can only be scored on events, so the first thing needed is the count of top and bottom episodes the history actually contains, with no factor attached. Rule: T(h, x) is true on day t when the lowest close in the next h days, excluding day t, is at least x below the close on day t. B(h, x, y) is true when the highest close in that window is at least x above today and no close in the window is more than y below today. Primary definitions are T(30, 15%) and B(30, 15%, 7%); neighbours are T(20, 10%), T(60, 25%) and B(60, 30%, 10%). An episode is a run of consecutive true days counted as one. Horizon: the h inside each definition. Pass: the labels exist, a label at t does not change when prices after its window are perturbed, and the episode counts are posted for BTC alone and pooled across assets, by period and by year. Fail: a label at t depends on a bar outside its window. This item admits nothing. The counts bound every detector that follows, and a definition that fires on a large share of days is reported as too loose rather than tightened after seeing the number.

Verdict: recorded, not admitted. No factor was tested, so there is no edge and no correlation to report. The definitions are too loose for the 15 to 25 episodes the program expected. On BTC, T(30, 15%) is true on 500 of 2,496 decided days, a day rate of 0.2003, in 61 episodes, and 2021 alone holds 30 of them. The validation period has 8 and the test period 2. B(30, 15%, 7%) is 72 episodes, day rate 0.2672, with 5 in the test period. Pooling the 20 names and counting a day once gives 94 top episodes and 115 bottom episodes, against 1,653 and 1,975 summed per asset, so the assets move together and the sum is not a sample size. The tightest neighbour, T(60, 25%), is the only one near the expected range: 26 BTC episodes, and zero of them in 2023 or 2024. results/2026-11-01_weekly.json. regime_tester/episodes.py, 21 tests passing. The score is unchanged.

## 2026-11-01, weekly retest of the three removed factors

Candidate: weekly_retest. The three factors removed on 2026-10-27 stay out unless they pass again on the current panel. Rule: top quintile minus bottom quintile of the factor, net of the thin-tier costs, non-overlapping windows at 10 days, same sign in both halves on BTC and the alt basket, and adding the factor must widen the out-of-sample gap of the live four-factor score. Correlation with the four live factors is reported either way.

Verdict: all three stay out. basis_btc_z30 is negative in both halves on BTC, train -1.5031 percent (t=-0.3943, n=17) and test -0.4953 percent (t=-0.14, n=12), so it points the wrong way, and its train alt cell rests on 3 observations. basis_gap_btc_eth keeps the caution sign on both assets and both halves, the best of the three, but its largest cell is n=16 and no t-stat clears 2 except the train BTC cell (t=-2.224, n=9). Adding it shrinks the alt basket out-of-sample gap from 4.4606 to 1.8764 percent. Its correlations with the live factors are all below 0.05, so it is not a duplicate; it is too thin. dispersion_14 flips sign on both assets, train +2.3589 percent to test -4.2209 percent on BTC. results/2026-11-01_retest.json. The score is unchanged.

## 2026-11-01, BTC at 1 day and 3 days

Candidate: btc_short_horizon. The four live factors scored on BTC at 1 day and 3 days, the horizons the program names and the only ones not yet reported on the current panel. Same rules as the three-period test: net of costs, non-overlapping, sign must hold in validation and test.

Verdict: rejected. No cell clears a t-stat of 2. The only one that keeps its sign at both horizons is btc_ret_30: at 3 days, validation +1.0825 percent (t=0.9216, n=25) and test +0.9164 percent (t=0.8399, n=20). At 1 day the test spread shrinks to +0.0717 percent (t=0.146, n=56). btc_vol_z90 and btc_trend_stretch flip negative in the test period at 3 days, and eth_funding_z30 is negative in both held-out periods at both horizons. The one cell that moved when the panel gained its 2026-10-31 row is eth_funding_z30 at 3 days in test, from -0.4769 percent (n=23) to -0.6555 percent (n=24). results/2026-11-01_three_period.json. The score is unchanged.

## 2026-11-02, pre-registered before any computation: positioning event tests

Candidate: positioning. Hypothesis: an extreme in funding, open interest, liquidations, the long/short ratio or basis, read from data known before the day, raises the chance that a top or a bottom episode starts within the horizon, above the base rate of episode starts. Rule: each factor is lagged one bar. The extreme is a 1-year rolling percentile, past data only, at or above the 90th for a top and at or below the 10th for a bottom. Neighbours are the 85th and 95th, and the 5th and 15th, reported beside the primary and not used to choose it. Streaks use the 80th and the 20th, with neighbours of 3 and 7 days around a primary of 5. The label is not the loose primary from 2026-11-01. It is T(60, 25%) and B(60, 30%, 10%), the only neighbour already inside the 15 to 25 episode range the program expected, fixed here before any factor is scored. An episode start is the first day of a run. A reading fires when it is extreme and no episode of that side has started in the prior h days, so one episode is counted once. Horizon: 60 days, the h inside the label. Pass: lift above 1 with the same sign in validation and in test, on BTC and on the pooled panel, the bootstrap 90 percent interval on the lift excludes 1 in both held-out periods, at least 40 independent episodes in each held-out period, and the neighbour cuts do not flip the sign. With more than 20 tests since the last admission the t-stat bar is 3; the same count raises the lift bar only by requiring the interval to exclude 1, which is already the rule. Fail: the sign flips in validation or in test, the edge sits in one calendar year, or it exists at the primary cut and vanishes at both neighbours. Fewer than 40 independent episodes in a held-out period is insufficient, not a rejection. Factors that cannot be built from retained history are recorded as not tested. This item does not change the score.

Verdict: rejected because no factor keeps a lift above 1 in both validation and test on BTC and on the pooled names. The best cell is ETH funding 7-day average at the 10th percentile on the bottom label: validation lift 1.516122 (42 fires, 37 hits) and test lift 2.087316 (30 fires, 29 hits), and the 5th and 15th cuts hold. The same factor on BTC flips, validation lift 2.118158 (29 fires) to test lift 0.431313 (45 fires). Of the 20 names, 6 keep the lift above 1 in both held-out periods and 8 flip. ETH has 85 bottom episodes against 47 on BTC, and the base rate of a start within 60 days is 0.676519, so the label is still too loose on ETH and the lift is measured against a high base. No cell has 40 independent episodes in both held-out periods. Open interest and liquidations start in 2022-09, so their train window is short. Cross-venue funding dispersion and days since the last cascade were not tested: the retained file is one venue, and no cascade definition was pre-registered. results/2026-11-02_positioning.json. The score is unchanged.

## 2026-11-02, pre-registered before any computation: D1 full perp universe, slice d1_inventory

Verdict: insufficient. The inventory covers today's listings only, so the point-in-time universe cannot be built. 2,092 USDT perps returned history, 755 Binance, 815 Bybit, 522 OKX, and every one of them has its last bar on 2026-11-02. Zero are inactive. Delisted names do answer by symbol: FTTUSDT_PERP.A returned 214 bars ending 2022-11-14 and SRMUSDT_PERP.A returned 802 bars ending 2022-11-15, and neither is in future-markets. No endpoint lists them. include_delisted=true returned the same list and /delisted-future-markets returned 404. results/2026-11-02_d1_inventory.json. The score is unchanged. Two tests since the last admission.

Candidate: d1_inventory. Hypothesis: Coinalyze serves every USDT perpetual on Binance, Bybit and OKX by symbol, including names that have since been delisted, so a point-in-time universe can be built from each name's first and last retained daily bar rather than from today's listings. Rule: pull the future-markets list, keep is_perpetual with quote_asset USDT and exchange in A (Binance), 6 (Bybit), 3 (OKX), then request daily ohlcv-history from 2020-01-01 to the end date taken from the clock for every symbol, in batches of 20. A name is in the inventory when that request returns at least one bar. First bar, last bar and bar count are recorded per symbol. A name whose last bar is more than 14 days before the pull date is marked inactive, which is the only delisting evidence this source can give. Horizon: none. This slice builds the name list and the first-date inventory. It does not score a return and it does not admit a factor. Pass: data/universe.json exists, every symbol in it was returned by the history endpoint rather than assumed from the market list, the count of names with history and the count of inactive names are posted, and the script resumes from the symbols already saved. Fail: the history endpoint returns only names in the current market list, so delisted names cannot be reached, or the request fails. Neighbour check does not apply; there is no threshold. The full six-series panel is a later slice and is not claimed by this one.

## 2026-11-02, pre-registered before any computation: D1 delisted-name list, Binance

Verdict: recorded, not admitted. The list the earlier slice could not find exists, but only for Binance and only as prices. The public archive holds 923 USDT perps that ever traded, 892 still publishing and 31 whose last file is before 2026-10-19. All 31 answer on Coinalyze when requested by symbol, and 30 of them are absent from future-markets, which is why the inventory of 2,092 showed zero inactive names. Bybit and OKX have no archive of this kind, so the three-venue list is not done. results/2026-11-02_d1_delisted.json. The score is unchanged. Three tests since the last admission.

Candidate: d1_delisted. Hypothesis: the Binance public archive lists every USDT-margined perp that ever traded, including names Coinalyze no longer enumerates, so the delisted-name list can be built from the archive's folder names and each name's first and last daily file. Rule: read the bucket listing under data/futures/um/daily/klines/ to the end of the pagination, keep every folder ending in USDT, then read each symbol's 1d listing to its last page and record the first file date, the last file date and the file count. A name whose last file is before 2026-10-19 is marked stopped. Horizon: none. This slice builds the Binance name list only. It does not score a return and it does not admit a factor. Pass: the symbol count equals the number of USDT folders in the bucket, every symbol has a first and a last file date taken from the listing rather than assumed, and the count of stopped names is posted. Fail: the bucket listing cannot be read to the end, or a symbol's last file date comes from a truncated page. Neighbour check does not apply; there is no threshold. Bybit, OKX and the six-series history are later slices and are not claimed by this one.

