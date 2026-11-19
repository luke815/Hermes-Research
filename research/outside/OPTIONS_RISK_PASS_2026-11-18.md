# Pass 2: options tape, positioning overlays, timeframes, and the risk-off dial (2026-11-18)

Question asked: do options and positioning data give a usable "market is overheating, take risk off" reading for a
crypto portfolio manager, and is there conditional or term-structure information the single-threshold pass missed?

Data: Deribit options by tenor from 2019-03 (25d skew, risk reversal, butterfly, ATM IV, IV/RV), DVOL from 2021-03,
futures and perp open interest from 2021-03, put/call OI ratio 2020-09 to 2025-03/06 (not served after), BTC/ETH
prices from 2019-01, hourly options and prices for the last two years. 18 alts from the dashboard file.
Method: PREREG2.md (below), written before scoring, with a risk addendum (forward drawdown, 10% crash probability,
false-alarm rate) and one amendment (risk cells at the quintile, 20-episode bar) recorded before the families ran.
About 330 return cell-horizons and 320 risk cell-windows on daily data, 72 hourly rows, 9 conditioned alt rows.
Entry one day after the signal (lag=1), costs per leg, carry charged, drift-controlled excess spreads.

## Bottom line

No daily return cell and no daily risk cell passed. With roughly 650 daily tests, about 3 to 6 passes were expected
by chance; zero is what "no usable one- or two-layer signal" looks like. No risk-off dial could be built: the rule
needs two independent risk-off cells to pass and none did. The four mechanical passes in the whole run are hourly,
risk-ON, the opposite sign to the hypothesis, and are vol clustering at a 24-hour window (low implied vol -> low
realized vol -> small moves), not a dial.

## A harness bug found by the refuters, fixed, and its effect

The rolling percentile treated a missing day as "lowest ever" (percentile 0.0), so a gap in a series fired a false
"bottom decile" flag. It affected only bottom-side cells on gappy series: 6 days of OI-weighted funding, 107-116
days of per-tenor skew/risk reversal, 25 days of IV/RV and 187 days of put/call ratio. It is fixed (harness.pct_rank
returns NaN on a missing day) and every cell it could have touched was re-run at lag=1:
- Pass 1's single pass (OI-weighted funding bottom decile, BTC, 1-day) is unchanged in substance: passes at lag 0,
  fails at lag 1 (validation t 1.06). Nothing in pass 1 changes verdict.
- IV/RV bottom ("options cheap -> down"), the strongest-looking pass-2 pattern before the fix, shrinks to 2-4
  validation episodes on ETH and nothing on BTC. It is not a finding.
- "Calls bid" (skew bottom) BTC: sign differs across periods after the fix.
- Put/call ratio cells were mostly artefact in validation; the series also ends mid-2025. Unscored until extended.

## Risk-off readings, post-fix, honest version

Only one overheating reading has deeper drawdowns in train AND test on BTC: the retail long/short ratio in its top
fifth of the trailing year. Forward 10-day drawdown effect -1.9 / -0.1 / -3.4 points (train / validation / test),
crash lift 1.6 / 1.2 / 3.3, false alarms 48-52%, 11-19 episodes, validation t -0.1. Validation is flat; ETH has the
wrong sign in train. This is a watch item, not a signal: a historical base rate from a thin sample.
The ATM term-structure inversion (7-day IV above 90-day IV) looked like a second watch item before the fix; after it,
the 20-day drawdown effect flips sign in validation on both assets. Downgraded to "no".
Every other "overheated" candidate points the other way or nowhere: funding, futures OI, perp OI and basis at their
highs were followed by SHALLOWER drawdowns than average in 2021-2024 (perp funding decile t +2.9 to +3.6 on both
assets, crash lift 0.4-0.7), mostly shallower in 2024H2-2025, and deeper only in 2026 where they barely fire.
Crowded longs have been a sign of a healthy trend, not a top, in this sample.

## Options as a direction signal
2019 and 2026, the fresh windows for the "options market is right" hypotheses, disagree with each other and with
2020-2025. In 2026 every options extreme, puts bid or calls bid, was followed by a bounce on both assets: a single
regime, not a direction read. The only stable sign across all three periods is weak (ATM inversion and 90-day skew
top -> weakness on ETH, validation |t| <= 2.1, 10-22 episodes).

## Conditional layers
130 conditioned cells: none added lift over its parent in both train and validation except "funding bottom AND
uptrend" on BTC (validation t 0.0-0.1, 16-18 episodes). The pairs with the best stories (fear + leverage, complacency
+ leverage, hedged + fearful) either flip sign with the period, never co-occur in a period, or ran out of data when
the put/call series ended. "Skew elevated without vol" was followed by weakness in train and test on both assets, the
opposite of the pre-registered "hedging, not panic" story, on 5-13 episodes: a candidate for Hermes, not a finding.

## What this means for the desk
- Do not put a positioning-based "overheated" light on the dashboard. The data says the usual overheating tells
  (funding, OI, basis highs) preceded calmer periods, not crashes, in 2021-2025.
- One watch item may be shown, clearly labelled as a base rate: BTC long/short ratio in its top quintile.
- The thing that did predict drawdowns best in-sample, cheap options relative to realized vol (IV/RV bottom), reversed
  completely in 2026 and rests on a handful of episodes after the fix. Watch, do not act.
- Nothing here changes the pass-1 conclusion: on public daily data, 2019-2026, BTC and ETH, there is no
  single-threshold or two-layer options/positioning signal that survives honest out-of-sample tests at 1-30 days.

## For Hermes: confirm on the full universe, in this order (replaces P2-P4 of the pass-1 list)
Q1. Long/short ratio top quintile -> deeper 10-30 day drawdowns, every coin and venue on the Laevitas panel
    (ls_ratio_level pct365 >= 0.8), lag=1, episodes >= 20, both the drawdown and crash-lift targets.
Q2. "Skew elevated without vol" (skew_30 pct >= 0.9 AND DVOL pct <= 0.2) -> weakness, BTC and ETH, on the 2019-2020
    and 2026 windows only, as a new hypothesis.
Q3. IV/RV bottom -> down and deeper drawdowns: is the 2026 reversal the rule on a broader universe or the exception.
Q4. Extend the put/call OI ratio past mid-2025 (L9), then re-run the three pc_ratio pairs.
Not worth more time: contrarian skew/butterfly "panic = bottom" (flips out of sample on both assets), funding/OI/
basis highs as a sell signal, DVOL-bottom complacency as a sell signal, hourly funding/OI (no history), conditioned
alt reversal, calm-regime momentum, single-threshold skew or risk-reversal direction reads.

---

# Agent synthesis (pre-fix numbers for IV/RV and ATM-slope cells; see the fix section above)

## Headline

Pass 2 scored six pre-registered families on BTC and ETH daily data 2019-2026 (options term structure, options direction with fresh 2019 and 2026 confirmation windows, twelve positioning overlays, vol regime, hourly, conditioned alts) plus the risk addendum: about 330 daily return cell-horizons and about 320 daily risk cell-windows at the fixed thresholds, plus 72 exploratory hourly rows, against PREREG2's planned counts of roughly 217 and 96. Zero daily return cells and zero daily risk cells passed; the only four PASS verdicts in the whole pass are exploratory hourly risk-ON cells (DVOL in its bottom quintile or decile → shallower 24-hour drawdowns, both assets), which carry the opposite sign to the pre-registered "complacency → risk-off" hypothesis, do not extend to 72 or 168 bars, and do not hold on daily data. PREREG2 expected roughly 3 return and 3 risk passes by chance at the 2.5 bar on the smaller planned counts, so zero passes on counts 1.5x to 3x larger is what "no usable single- or two-layer signal" looks like; the one risk-off candidate with the same direction in all three periods (BTC long/short ratio top → deeper drawdowns) has 12-19 independent episodes against a bar of 20 and validation t between -0.1 and -0.7.

## Risk-off dial: what the data supports

No daily risk cell met the risk-off rule (mdd deeper in all three periods, validation |t| >= 2.5, crash lift >= 1.5 validation / >= 1.2 test, >= 20 episodes, validation false alarms < 60%). The cells below are the ones that came closest or that are informative because they fail in a specific way. Drawdown effect is the mean forward maximum drawdown on flagged bars minus on all bars (negative = worse than usual), train / validation / test. Crash lift is P(-10% drawdown within W days | flag) / P(-10% drawdown within W days). False alarms = share of flagged bars whose 20-day forward return was positive (validation).

| Cell | Asset | W (days) | Drawdown effect tra / val / test | Crash lift val / test | False alarms (val) | Verdict |
|---|---|---|---|---|---|---|
| lsr top, quintile | BTC | 20 | -4.0% / -0.7% / -3.8% | 1.34 / 2.03 | 0.52 | insufficient: 16 episodes; val t -0.5 |
| lsr top, decile | BTC | 10 | -2.0% / -0.8% / -7.6% | 1.79 / 5.02 | 0.52 | insufficient: 19 episodes; val t -0.7 |
| lsr top, decile | BTC | 20 | -3.7% / -1.0% / -7.9% | 1.54 / 2.79 | 0.52 | insufficient: 15 episodes; val t -0.6 |
| lsr top, quintile | BTC | 10 | -2.3% / -0.1% / -3.4% | 1.23 / 3.28 | 0.52 | rejected: val t -0.09 |
| lsr top, quintile | ETH | 20 | +0.4% / -1.0% / -4.3% | 1.09 / 1.93 | 0.35 | insufficient: 14 episodes; wrong sign in train |
| ATM term slope top, quintile (H1) | BTC | 10 | -1.4% / -1.7% / -0.6% | 1.35 / 1.29 | 0.39 | rejected: val t -2.06 (33 episodes) |
| ATM term slope top, quintile (H1) | ETH | 10 | -1.9% / -1.1% / -0.9% | 1.37 / 1.37 | 0.53 | rejected: val t -0.7 (47 episodes) |
| DVOL bottom, quintile | ETH | 10 | +0.8% / -3.3% / -0.8% | 1.92 / 1.31 | 0.28 | insufficient: 10 episodes; wrong sign in train; BTC points the other way |
| IV/RV bottom, decile | ETH | 20 | -2.5% / -8.8% / +4.2% | 1.99 / 0.43 | 0.11 | rejected: sign flips in 2026 |
| IV/RV bottom, quintile | BTC | 20 | -0.6% / -1.8% / +3.1% | 1.73 / 0.21 | 0.43 | rejected: sign flips in 2026 |
| skew_30 1-day jump z >= 2 (H2) | ETH | 10 | +0.8% / -4.2% / -0.5% | 1.83 / 1.66 | 0.25 | rejected: train wrong sign (38 episodes) |
| skew_30 1-day jump z >= 2 (H2) | BTC | 10 / 20 / 30 | +1.0 / -0.2 / -4.1%; +0.9 / -0.4 / -6.9%; +0.7 / -0.2 / -5.2% | 0.95 / 3.09; 0.96 / 2.51; 1.10 / 1.63 | 0.50 | rejected: effect exists only in 2026 |
| DVOL bottom AND futures OI top, decile (H3 d) | ETH | 10 | +1.8% / -6.0% / no bars | 2.44 / - | 0.25 | insufficient: 2 validation episodes, 0 test bars |
| IV/RV top, decile (mirror cell, hypothesis risk-ON) | ETH | 20 | +1.6% / -1.7% / -11.2% | 1.24 / 2.19 | 0.32 | insufficient: 18 episodes; direction is risk-OFF, opposite to hypothesis |
| perp funding top, decile ("crowded longs") | BTC | 20 | +2.8% (t +3.0) / -0.2% / -0.1% | 0.71 / 1.19 | 0.37 | insufficient: 8 episodes; drawdowns were SHALLOWER after crowded longs in 2021-2024 |
| perp funding top, decile | ETH | 10 | +2.4% (t +3.3) / +0.8% / -0.6% | 0.70 / 1.41 | 0.60 | rejected: shallower in train and validation |
| skew term slope top, decile (H1, contrarian "panic = bottom") | BTC | 20 | +4.0% (t +5.4) / -0.8% / +0.6% | 0.00 / 0.00 | 0.00 (2 episodes) | insufficient: 18 episodes; train says shallower, validation says deeper |

Dial calibration table: not built. PREREG2 requires at least two independent risk-off cells to pass, and the amendment requires a cell to be at least "broad" in both assets or in two windows. Nothing passed at either threshold, so there is no rule-based dial to calibrate. Building one from the near-misses would be fitting after the fact.

Plain-language reading of the one direction that held across periods: when BTC's long/short ratio sat in the top fifth of its trailing year, the worst point of the next 20 days was on average 0.7 to 4.0 points lower than usual depending on the period, and a 10% drop within 20 days was 1.3 to 2.0 times as common. But in 2024H2-2025 the effect was 0.7 points with t -0.5, 52% of those flagged days still ended higher 20 days later, and the whole record is 16 separate episodes. That is a historical base rate from a thin sample, not a forecast, and it is BTC only (ETH has the wrong sign in 2021-2024). The other "overheating" readings a PM would reach for (funding top, futures OI top, perp OI top, basis top, and the funding-and-OI and basis-and-funding pairs) point the wrong way: in 2021-2024 the 10-30 days after crowded-long extremes had shallower drawdowns than average (perp funding decile t +2.9 to +3.6 on both assets, crash lift 0.4-0.7), mostly shallower in 2024H2-2025 too, and they turn negative only in 2026 where they rarely fire (futures OI top never fires in 2026 on BTC, once on ETH).

## Options as a direction signal

H2 was designed so the sign would be confirmed only on data pass 1 never used: 2019 and 2026. Those two windows disagree with each other and with 2020-2025.

2019 slice (percentile recomputed on the slice, 114 valid bars from late September): the "tops" never fire (max percentile 0.73-0.75), so 2019 speaks only to the bottom-side cells. Calls bid → UP is contradicted: skew_30 bottom has negative excess at all five horizons on both assets (BTC -1.05% to -12.13%, ETH -0.86% to -9.57%), from 1-8 bars. rr_30 bottom (puts bid → DOWN) is negative on ETH at 1-5 days and positive on BTC at every horizon. Every row is "insufficient" (fewer than 3 flagged bars in a period) by construction.

2026 slice: every one of the 40 populated rows for skew_30 top and rr_30 bottom (puts bid) has positive excess (BTC skew top h=5 +4.20% t 2.8; ETH h=20 +15.42% t 4.4; 1-6 episodes each), and every one of the 20 populated calls-bid rows is positive as well. When both tails of the same series go up, the options tape is not giving a direction; 2026 is a single regime in which any extreme preceded a bounce. The full-panel 2026 test rows agree in sign at 1-5 days.

2020-2025 (train and validation): on BTC, puts-bid cells have positive excess (opposite to the hypothesis) in train at every horizon and in validation at most horizons; on ETH, skew_30 top does carry the hypothesised negative sign in train and validation at all five horizons (validation -0.47% to -5.88%, |t| 0.9-1.8) before 2026 flips it. Calls bid → UP has the right sign almost everywhere but never clears the bar: the best cell is skew_30 bottom BTC h=5 (+0.25% / +1.70% / +0.67%, validation t 2.08, 41 episodes, validation net +1.46%), and train net is negative at 1-5 days in 7 of 8 calls-bid cells. DVOL top → DOWN holds only in train (BTC h=20 -6.69% t -3.3 from 5 episodes), has fewer than 3 BTC validation bars, flips on ETH in validation and on BTC in 2026. Fast repricing (1-day skew jump, z >= 2) has no sign-stable cell: BTC is negative at every horizon in 2026 (h=20 -8.62% t -2.8) and positive in train; ETH is negative in validation (h=5 -5.23% t -2.1) and positive in 2026. On BTC both skew_30 tails are positive at 1-5 days in all three periods, which rules out reading them as direction.

Term-structure cells (H1): the pre-registered story, front-end skew panic is contrarian-bullish over 3-10 days, is a 2019-2024H1 phenomenon. BTC skew term slope top had +1.75% / +3.11% / +6.10% train excess at h=5/10/20 (t 2.6/2.6/2.5) and negative excess in validation and test at every horizon on ETH and every horizon but one on BTC (BTC validation h=20 -6.37% t -4.0; ETH -13.94% t -4.8, from 1-2 episodes). The risk mirror flips the same way: train drawdowns shallower on both assets (BTC decile t 4.6/5.4/4.2), validation deeper on both. Signed butterfly top does the same. Where the term structure has a stable sign it is "fear is right", not contrarian: inverted ATM term structure (atm_slope top) is negative on BTC in all three periods at h=3-20 (validation -0.73% / -0.69% / -1.72% / -2.81%) and gives deeper 10-day drawdowns on both assets in all three periods, with crash lift 1.3-1.4, but validation |t| <= 2.1 and 14-22 episodes. 90-day skew top on ETH is negative in all three periods at all five horizons, growing with horizon (h=20 -6.71% / -3.28% / -5.06%), validation |t| <= 0.9, 8-22 episodes. Butterfly top on |return| gives larger moves only at 1 day and smaller moves than usual at 10-20 days out of sample (ETH h=10 validation -4.29% t -4.1). Note also that the skew term slope itself changed level: BTC mean 5.08 in train, 5.00 in validation, 0.04 in 2026 (ETH 4.89 / 4.96 / 2.19); the front-end skew premium largely disappeared in 2026, so 2026 top-decile flags fire in a different regime.

## Conditional layers

H3 scored 130 cell-horizons (12 pre-registered pairs, k split into k1/k2, both assets) and 66 risk cell-windows: 0 passes, 123 insufficient, 7 rejected. The PREREG2 rule for a conditioned cell is that the lift over the unconditioned parent is positive in train AND validation, with the parent pointing the same way in validation.

Only one combination meets the lift condition, and it is empty of statistics: e_btc (funding bottom decile AND price above its 50-day mean → UP) at h=10 and h=20 has positive excess in all three periods (+1.46% / +0.02% / +1.18%; +2.88% / +0.35% / +1.08%), lift +1.74 / +0.93 and +3.68 / +2.58 points over the parent in train / validation, but validation t 0.0 and 0.1 and 18 / 16 episodes. The pass-1 "funding bottom → up" story reappears only out of sample, only on ETH, only in an uptrend (e_eth validation h=10 +4.70%, h=20 +3.79%), and on ETH in train the same cell is -9.50% (t -3.6) and -15.37% (t -5.8): the sign depends on the period.

Everything else is interaction mining or data-starved:
- d (DVOL bottom AND futures OI top → DOWN) has negative excess at every horizon in train and validation on both assets (ETH train t -1.8 to -3.7, validation up to -2.7), but the lift is negative at every horizon in both periods on both assets: the unconditioned DVOL-bottom parent is more negative, so the OI overlay subtracts information. Test has 0 flagged bars (OI top never fires in 2026).
- i (ATM inversion AND OI top → DOWN): negative at every horizon in train (BTC h=10 t -3.8), positive at every horizon in validation (BTC h=20 +8.44%); lift negative throughout train and positive throughout validation. A clean example of a conditioner that flips with the period.
- k2 (skew top AND DVOL bottom → UP, "hedging not panic"): the wrong sign consistently. Excess negative in train and test on both assets (BTC h=10 -7.85% / -5.13%; ETH -5.98% / -3.89%), and on risk targets deeper drawdowns in train and test with test crash lift 2.0-4.3. Validation is positive or empty. If anything this is a weakness reading, not a buy-the-dip reading, but 5-13 episodes.
- b (skew top AND OI bottom → UP) has negative train excess at h=10 on both assets (-2.92%, -6.96%) and positive test; k1 (skew top AND DVOL top → DOWN) negative in train, positive in test. a (skew top AND OI top) never co-occurs in train on either asset and never in test; its only data are 36 BTC / 5 ETH validation bars, where ETH is positive (h=5 +6.67% t 2.8, 3 episodes), opposite to DOWN.
- g, h, l (put/call ratio cells) have 0 test bars because the series ends 2025-03-31 (BTC) / 2025-06-30 (ETH), and h's validation flags are 100% a harness artefact (see Data limits). j_btc is 3-4 train bars; j_eth's lift is exactly zero because every butterfly-top bar in validation is also an OI-top bar.
- Risk pairs: mdd difference is positive (shallower) for d on both assets in train and for a, d_btc and i in validation. The only deep-drawdown readings with crash lift above 1.5 are d_eth validation (decile W=10 -6.0% t -3.5, lift 2.44, 2 episodes, train positive, no test bars) and h_eth, whose validation is artefact.

Net: the second layer did not add lift where it had a story, and where the numbers look strong (i train, k2 test, d_eth validation) they are single-period, 2-13 episodes, and reverse in the next period.

## Hourly

H5 is exploratory per PREREG2 (train 6.5 months after warm-up, validation 6 months, test 10.5 months). 0 of 48 return cell-horizons pass. The fear reads (skew_30 top and rr_30 bottom, which are the same cell within a few bp at every horizon) are negative in train at every horizon (ETH t -2.0 to -3.0), positive in validation at every horizon (t +0.5 to +2.2), and negative again on ETH in 2026; 16 of 16 fear cell-horizons show the train/validation flip, and the skew-top risk cells flip the same way (deeper drawdowns in train and test with crash lift 1.2-4.8, shallower in validation). The four PASS verdicts are DVOL bottom at W=24 bars, both assets, both thresholds, risk-ON (validation mdd +0.3% to +0.8%, t 2.7-4.0, crash 0/845 to 1/2747), labelled "sharp" by the amendment. They should not be used: the hypothesis was risk-OFF, a 10% drop inside 24 hours is essentially absent in the sample (base rate 0.1-0.2% on BTC), flagged forward realised vol is 30% vs 40% average, so the pass is "low implied vol → low realised vol → shallow one-day moves"; it breaks at 72 and 168 bars (test crash lift 1.1-1.7), and the daily DVOL-bottom cells do not confirm it (BTC deeper in train, ETH deeper in validation and test). Hourly funding and OI start 2025-09-28 and are unscorable. At 4 bars no cell has |excess| above 0.3% and validation net after costs is <= +0.01% everywhere.

## Alts conditioned

H6 scored 9 cell-horizons: 0 passes, 3 insufficient (DVOL >= 0.8 holds on only 17 validation days, 7 episodes), 6 rejected. Every reversal variant, conditioned on DVOL top or on an OI flush, the two exploratory pairings, and both unconditioned lag-1 parents, has a negative long-short spread and negative IC in 2026 at every horizon (parent 1-day reversal test t -2.11, IC -0.041 t -2.67): in 2026 the 1-3 day alt losers kept losing. OI-flush conditioning makes validation the one positive period (+0.61% / +1.36% / +1.39%, lift +0.41 / +1.12 / +1.53 points over the parent) but train and test are negative, and the parent shows the same train-negative / validation-positive / test-negative shape, so the condition inherits a sign flip rather than fixing it. Calm-regime conditioning (DVOL <= 0.5) makes 14-day momentum weaker, not stronger: lift is negative in train and validation at every horizon (-0.04 / -0.19 / -0.39 and -0.17 / -0.37 / -0.53 points), and the momentum spread is positive while the full-rank IC is negative in every period, the same tail-versus-middle disagreement seen in pass 1. Net after 60 bps round trip is negative at 1 day for every cell and period except one.

## Patterns that are consistent but not significant

- Every "fear is contrarian-bullish" cell is a train-period artefact. Skew term slope top, signed butterfly top and IV/RV top (options rich → UP) are positive in 2019-2024H1 on both assets and negative in both 2024H2-2025 and 2026 on both assets, on returns and on drawdowns alike.
- Where a fear measure has a stable sign across all three periods, it is "fear is right": ATM inversion on BTC (negative at h=3-20), 90-day skew top on ETH (negative at all horizons), 10-day drawdowns deeper after ATM inversion on both assets. All with validation |t| <= 2.1 and 10-22 episodes.
- IV/RV bottom (options cheap vs realised) → DOWN holds in train and validation on both assets at every horizon (ETH validation h=10 -8.64% t -4.2, h=20 -14.54% t -3.9; ETH decile W=20 drawdown -8.8% t -4.2, crash lift 1.99) and reverses on both assets at every horizon in 2026 (drawdowns shallower, crash lift 0.1-0.65). Twenty-two of the BTC train flags are artefact bars, and with those removed BTC train excess goes to about zero.
- Crowded longs did not precede crashes in 2021-2024: funding top, OI top, basis top and their pairs all show shallower drawdowns in train (t up to +3.6), mostly shallower in validation, and deeper only in 2026 where they barely fire.
- BTC long/short ratio top is the only overheating reading with deeper drawdowns in all three periods at both thresholds and all windows (crash lift 1.2-5.0), with 12-19 episodes and validation t -0.1 to -0.7. ETH has the sign only out of sample.
- 2026 reverses the validation sign for almost every H4 cell and reads every options extreme, puts-bid or calls-bid, as bullish on both assets. A single-year test period with one regime cannot confirm anything that validation suggested.
- Calls bid → UP has the right sign in 15/15 BTC skew-bottom period-rows and in most ETH rows, with a best validation t of 2.08 and train net negative at 1-5 days in 7 of 8 cells.
- k2 ("skew without vol") is followed by weakness in train and test on both assets, the opposite of the pre-registered story, with 2-13 episodes.
- ETH DVOL bottom ("complacency") gives deeper drawdowns in validation and test (crash lift 1.2-1.9) but not in train; BTC does the reverse. The two assets disagree.
- Hourly fear reads flip sign between train and validation in 16 of 16 cell-horizons.
- Alt 1-3 day reversal is negative in 2026 in every variant.

## What is dead on this data

- H1 term structure of fear: front-end skew panic as a contrarian buy is dead (train-only, flips sign out of sample on both assets, on returns and drawdowns); the remaining stable sign (inversion → weakness) is below every bar.
- H2 options direction: dead as a single-threshold read; 0/70 pass, both skew tails positive on BTC, 2019 and 2026 disagree on calls-bid, 2026 reads puts-bid as bullish, best validation t 2.08.
- H3 positioning overlays: dead; 0/130 pass, 123 insufficient on data count, the only pair with consistent lift (funding bottom AND uptrend, BTC) has validation t 0.0-0.1, and every pair with a story either flips with the period or has 0-2 test bars.
- H4 vol regime and overheating crash candidates: dead as stable signals; IV/RV has the right sign in 2020-2025 and reverses in 2026; funding/OI/basis tops precede shallower, not deeper, drawdowns in 2021-2024; lsr top BTC is the lone survivor and is below the episode and t bars.
- H5 hourly: dead; the fear reads flip between periods and the four risk-on passes are vol clustering at a 24-hour window, not confirmed on daily.
- H6 conditioned alts: dead; 0/9, every reversal variant negative in 2026, calm-regime conditioning reduces momentum.

## Data limits

- Harness artefact, not fixed in this pass: the rolling percentile returns 0.0 instead of NaN on bars where the raw series is missing but the window has enough history, so every "bottom" flag fires on gap days. The put/call ratio ends 2025-03-31 (BTC) / 2025-06-30 (ETH), producing 185 / 184 consecutive artefact flags in validation; cell h's validation is 100% artefact, cell l's train flags are 20/65 (BTC) and 30/45 (ETH) artefact because rr_30 has 118 / 100 internal gap days, and the NaN-masked rerun of l changes train excess materially (BTC h=20 -5.16% → -11.22%). IV/RV bottom on BTC has 22 artefact train days that carry most of its train DOWN sign. Top-side flags are unaffected. This must be fixed before any bottom-side cell is re-run.
- Options tenor series start 2019-03-31; with the 180-observation minimum, the first valid signal is late September 2019, so train is 2019-09..2024-06. Gaps are heaviest in 2024 (2024-02-02..03-01 has 25 of 29 days missing; 30 of 549 validation days are NaN for the skew slope).
- The pre-registered decile fires on 6 of 549 validation bars for skew slope, ATM slope and butterfly on both assets; validation statistics for those cells rest on 1-6 episodes (1-3 at h >= 5), and the 30-episode return bar is unreachable at h >= 10 (13-29 episodes). This is a property of the design, not the data: for the 10-20 day horizons a PM cares about, the return rules could not have passed anything at a decile cut.
- Futures OI, perp funding, perp OI, basis and DVOL start 2021-03, so every conditioned cell has at most about 2.8 years of train. Futures OI top never fires in 2026 (BTC max percentile 0.766; ETH 1 bar); basis top decile has 0 validation bars; DVOL top decile has 0 BTC validation bars; put/call cells have 0 test bars.
- Daily funding starts 2020-01-21; earlier net figures carry no funding cost.
- The skew term slope changed level in 2026 (BTC 5.08 → 0.04, ETH 4.89 → 2.19), so trailing-percentile flags in the test period fire in a different regime.
- Risk cells at W=20/30 have 4-19 episodes even at the quintile for most leverage and basis cells; only W=10 is adequately populated.
- Hourly: funding and OI from 2025-09-28 only; 19% of train hours have missing prices; 45-day percentile warm-up; the 24-hour crash event base rate is 0.1-0.2% on BTC.
- Alts: the cross-section harness counts consecutive conditioned days as independent (n_ind = n_days / h), so printed episode counts overstate independence (115 "independent" days are 13 clusters). 14 of the 18 alts have prices before 2021, not 7.
- Scope creep against the pre-registration: every family was run on both assets and risk at two thresholds, so roughly 330 daily return rows and 320 daily risk rows were scored versus the planned 217 and 96. Zero passes is still zero, but the chance baseline is higher than the one written in PREREG2.
- The 2026 test period is one regime. Several cells reverse their 2024-2025 sign in 2026; that is a statement about 2026, not about the cell.

## Recommendation

Dashboard risk reading. Nothing from this pass earns a place as a tested risk-off dial, and no dial was built because no risk-off cell passed. If the dashboard shows a positioning-based risk reading at all, show at most two items, both labelled "unconfirmed watch item, historical base rate, not a signal":
1. BTC long/short ratio in its top quintile of the trailing year. Evidence: deeper 20-day drawdowns in all three periods (-4.0 / -0.7 / -3.8 points), a 10% drop within 20 days 1.3-2.0x as common, but 52% of validation flags still ended higher 20 days later, validation t -0.5, 16 episodes, BTC only.
2. ATM term structure inverted (7-day IV above 90-day IV, top quintile of the trailing year). Evidence: deeper 10-day drawdowns on both assets in all three periods (BTC -1.4 / -1.7 / -0.6 points; ETH -1.9 / -1.1 / -0.9), crash lift 1.3-1.4 in validation and test on both, validation t -2.06 BTC and -0.7 ETH, false alarms 39-53%.
Remove or do not add: any "panic is a buying opportunity" reading from front-end skew or butterfly (sign reverses out of sample on both assets); funding, futures OI, perp OI or basis "overheating" as a sell signal (drawdowns were shallower after those extremes in 2021-2024, t up to +3.6); DVOL-bottom "complacency" as a sell signal (assets disagree, train disagrees with validation); skew or risk reversal as a direction read.

For Hermes to confirm on the full universe, in this order: (1) fix the percentile-on-NaN artefact and extend the put/call ratio past mid-2025 before re-running any bottom-side or pc_ratio cell; (2) long/short ratio top → deeper 10-30 day drawdowns, across more assets and venues (lsr is exchange-specific) to get past 20 episodes and to see whether ETH's wrong train sign is noise; (3) ATM inversion → weakness and deeper 10-day drawdowns, both assets, at the quintile; (4) IV/RV bottom → down and deeper drawdowns in 2020-2025 versus the 2026 reversal: is 2026 the exception on a broader universe or the rule; (5) the k2 "skew elevated without vol → weakness" sign, which is consistently opposite to the pre-registered story in train and test on both assets and would be a risk-off reading if it survives; (6) whether the 2026 "every options extreme is bullish" pattern is the single-regime effect it looks like.

Not worth more time on this data: hourly funding and OI (no history); conditioned alt reversal and calm-regime momentum; put/call cells until the series is extended; butterfly and 7-day-versus-90-day skew at the decile (too few episodes by construction); the 1-day skew jump z-score cells (no stable sign on either asset); the DVOL 5-day shock cell; the hourly DVOL-bottom risk-on passes (vol clustering, not a dial); and any further single-threshold direction test on skew or risk reversal.

---

# Pre-registration 2: options tape, term structure, positioning overlays, multiple timeframes

Written 2026-11-18 before any cell of this pass is scored. Builds on PREREG.md; the first pass found no single-threshold
signal at 1-10 days on the dashboard file. This pass asks whether the options market carries conditional or
term-structure information that a single blended series missed, and whether it works at other horizons.

## Data (pulled from Laevitas, Deribit options, Binance perps)
Daily from 2019 where served: 25d skew by tenor (7/14/30/60/90/180/365), 25d risk reversal by tenor, 25d butterfly by
tenor, ATM IV by tenor, DVOL, IV/RV, put/call OI ratio, options OI total, futures OI total, perp funding, perp OI.
Hourly for the last two years: DVOL, skew/RR/ATM IV by tenor, perp price, funding, OI where served.
Prices: daily from the dashboard file (BTC, ETH); hourly from Binance perps.

## Periods
Daily: train <= 2024-06-30 | validation 2024-07-01..2025-12-31 | test >= 2026-01-01 (as before). Series that start in
2019 add about two years of train versus the first pass.
Hourly (two years only): train 2024-11..2025-06 | validation 2025-07..2025-12 | test 2026. Short, so hourly results are
reported as exploratory unless they also hold on daily data.

## Fixed rules
Entry at lag=1 bar (the position is taken one bar after the signal bar closes). lag=0 reported only as an upper bound.
Primary thresholds: trailing-365-day percentile >= 0.9 / <= 0.1 (daily); trailing-90-day percentile for hourly
(>= 0.9 / <= 0.1). Conditioner thresholds: percentile >= 0.8 / <= 0.2. No other thresholds are tried.
Horizons: daily 1, 3, 5, 10, 20; hourly 4, 12, 24, 72 bars.
Statistics, costs, carry, independent-episode counts: harness.py, unchanged. Drift control: every spread is also
reported against the same-period mean (excess), and the verdict uses the excess version.

## Pass rule for this pass (stricter than pass 1, because there are more cells)
Single cells: same sign of the excess spread in all three periods; validation |t| >= 2.5; test same sign;
n_ind >= 30 across train+validation; validation net > 0 at lag=1.
Conditioned cells (primary AND conditioner): all of the above, AND the unconditioned primary cell has the same sign in
validation, AND the conditioned lift (conditioned spread minus unconditioned spread) is positive in train AND validation.
A conditioned cell whose parent points the other way is interaction mining and is reported as such.
Everything else: insufficient or rejected.

## Families and cells
H1. Term structure of fear (BTC and ETH, daily)
  - skew term slope = skew_7 - skew_90: pct top (front-end panic) -> up over 3-10d; pct bottom -> down
  - ATM term slope = atm_iv_7 - atm_iv_90: pct top (inverted, front-end stress) -> up over 3-10d; inversion flag (slope > 0) -> up
  - butterfly_30 pct top (tail demand both sides) -> large move either way: report |return| spread and the signed spread
  - skew_7 pct top vs skew_90 pct top: which tenor carries information (report both)
H2. Direction of the options market (new hypotheses, confirmed only on data pass 1 never used for sign: 2019-2020 and 2026)
  - puts bid: skew_30 pct top -> DOWN over 5-20d; rr_30 pct bottom -> DOWN
  - calls bid: skew_30 pct bottom -> UP; rr_30 pct top -> UP
  - DVOL pct top -> DOWN over 5-20d (fear is right, not contrarian)
  - fast repricing: skew_30 1-day change z30 >= 2 -> DOWN over 1-5d; <= -2 -> UP
H3. Positioning overlays (daily; conditioners at 0.8/0.2)
  Primary cells from H1/H2 and from pass 1's F3 (funding bottom decile -> up), each crossed with ONE conditioner:
  - futures_oi pct >= 0.8 (leverage high) / <= 0.2
  - options_oi pct >= 0.8 / <= 0.2
  - put/call OI ratio pct >= 0.8 (hedged) / <= 0.2 (unhedged)
  - perp funding pct >= 0.8 (crowded long) / <= 0.2 (crowded short)
  - trend: close above / below its 50-day mean
  Specific pre-registered combinations (the ones with a story), 1 conditioner each:
  a) skew_30 top AND futures_oi top -> DOWN (fear plus leverage = forced selling ahead)
  b) skew_30 top AND futures_oi bottom -> UP (fear with no leverage = washed out)
  c) DVOL top AND funding bottom -> UP (panic plus crowded shorts)
  d) DVOL bottom AND futures_oi top -> DOWN (complacency plus leverage)
  e) funding bottom AND trend up -> UP (crowded shorts in an uptrend)
  f) funding bottom AND trend down -> report; sign unknown
  g) pc_ratio top AND skew top -> UP (fully hedged market rarely crashes)
  h) pc_ratio bottom AND DVOL bottom -> DOWN (unhedged and complacent)
  i) ATM inversion AND futures_oi top -> DOWN
  j) butterfly top AND futures_oi top -> |return| large
  k) skew_30 top AND DVOL top -> DOWN (both fear measures agree) vs skew_30 top AND DVOL bottom -> UP (skew without vol: hedging, not panic)
  l) rr_30 bottom AND pc_ratio top -> UP
H4. Vol regime (daily)
  - IV/RV ratio pct top -> UP over 5-20d (options overpriced, realized calm follows) ; bottom -> DOWN
  - IV/RV ratio pct top AND trend down -> UP (capitulation priced)
  - DVOL 5-day change pct top (vol shock) -> report 1-5d and 10-20d separately
H5. Hourly (exploratory; BTC and ETH)
  - DVOL 1h pct90 top -> UP over 24-72 bars; skew_30 1h pct90 top -> DOWN over 12-72 bars; rr_30 1h pct90 bottom -> DOWN
  - skew_30 1h change over 4 bars z (90d) >= 2 -> DOWN over 4-24 bars
  - funding 1h pct90 bottom -> UP over 24-72 bars (if hourly funding is served)
  - OI 1h 24-bar % change pct90 top -> report
H6. Alt cross-section revisited with conditioning (18 alts, daily; the data limit stands)
  - 1-3 day reversal ONLY on days when BTC DVOL pct >= 0.8 (reversal is stronger in high-vol regimes): net after 30 bps per leg
  - 1-3 day reversal ONLY when BTC futures OI dropped > 5% in 3 days (post-flush)
  - 14-day momentum ONLY when DVOL pct <= 0.5 (calm regimes)

## Count
H1 8 cells x 5 horizons = 40; H2 8 x 5 = 40; H3 12 x 5 = 60 (+ the parent cells already in H1/H2/F3); H4 4 x 5 = 20;
H5 6 x 4 x 2 assets = 48; H6 3 x 3 = 9. About 217 cell-horizons, roughly 11 passes expected by chance at |t| 2, about
3 at |t| 2.5. A family is credible only when several related cells agree and the conditioned lift is consistent.

## Robustness on any pass
lag=2; neighbouring thresholds (0.85/0.95; conditioner 0.75/0.85); drop the best 3 validation days; ex-2020; and for
conditioned cells, swap the conditioner for its neighbour (futures_oi -> options_oi) and check the sign holds.

## Addendum, written 2026-11-18 before scoring: RISK targets (the owner's actual use is a risk-off dial)

The question for a portfolio manager is not "does this earn after costs" but "when this fires, is the downside ahead
worse than usual". So every primary and conditioned cell in H1-H4 (daily) is also scored against risk targets, on
BTC and ETH, with the SAME flags and periods:

Targets per signal bar t (position already held; the decision is to cut or keep):
  mdd_W   forward maximum drawdown over the next W bars: min over k<=W of close[t+k]/close[t] - 1, W in 10, 20, 30
  crash_W event: mdd_20 <= -10% (and -15% reported), W = 20
  rv_20   realized vol over the next 20 days (annualized)
  q05_20  5th percentile of the 20-day forward return among flagged bars vs among all bars
  missed  mean 20-day forward return on flagged bars (what you forgo by being risk-off) and the share of flagged
          bars with a positive 20-day return (false-alarm rate)

Statistics: mean mdd_W on flagged bars minus on all bars (negative = worse), Newey-West t with lag W; crash lift =
P(crash | flag) / P(crash) with the counts; AUC of the continuous signal for the crash event (rank-based, per period);
n_ind as before.

Pass rule for a RISK-OFF cell: mdd_20 difference negative in all three periods; validation |t| >= 2.5 on mdd_20;
crash lift >= 1.5 in validation AND >= 1.2 in test; n_ind >= 30 across train+validation; and the false-alarm rate in
validation below 60% (if most flagged periods still ended higher, the dial costs more upside than it saves).
A RISK-ON cell (washed-out, buy-the-dip) passes on the mirror: mdd_20 difference positive (shallower drawdowns), crash
lift <= 0.6 in validation and <= 0.8 in test, and mean 20-day return positive in validation.

Dial (only if at least two independent risk-off cells pass): equal-weight sum of the passing cells' flags, mapped to
0-100; its calibration table (dial bucket -> crash rate, mean mdd_20) is reported per period. Nothing is fitted; the
weights are equal by rule, so there is no in-sample tuning of the dial.

Added cells (risk-specific, daily, BTC and ETH): crash_W is also tested against the obvious "overheating" candidates
from pass 1 that failed on returns: funding pct top (crowded longs), futures/perp OI pct top, basis pct top,
lsr pct top, DVOL pct bottom (complacency), IV/RV pct bottom, pc_ratio pct bottom (unhedged), and the pairs
funding top AND OI top, DVOL bottom AND OI top, basis top AND funding top. 13 primary + 3 pairs, 2 assets, 3 windows.
Count: about 96 risk cell-windows on top of the 217 return cells. Roughly 3 risk passes expected by chance at the
2.5 bar; a credible dial needs agreement across windows and assets, not a lone cell.

## Amendment, 2026-11-18 14:40 UTC, after one smoke cell (skew_30 top, BTC) and before any family was scored
The 30-independent-episode bar from pass 1 was set for 1-10 day horizons. At 20-30 day drawdown windows, decile
extremes over 2020-2025 produce 7-18 episodes by construction (an extreme that lasts weeks is one episode), so the
risk cells would all be "insufficient" whatever the data said. For RISK cells only:
  - the primary threshold is the quintile (pct >= 0.8 / <= 0.2); the decile is reported beside it as the sharper cut;
  - the episode bar is 20 across train+validation, separation W bars, and the exact counts are always printed;
  - a risk cell that passes only at the quintile and not at the decile is labelled "broad", one that passes at both
    "sharp", and the dial uses only cells that are at least broad in both BTC and ETH or in two windows.
Return cells keep the pass-1 rules unchanged. This amendment was written before the risk families were scored; the
smoke cell seen (skew_30 top on BTC, decile) showed train mdd -3.8% t -1.4 and nothing out of sample.
