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
