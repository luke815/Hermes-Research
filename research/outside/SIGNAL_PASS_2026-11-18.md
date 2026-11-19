# Independent signal pass, 2026-11-18

Who: an outside pass run from the public dashboard data file (daily, 2020-01-21 to 2026-11-17: BTC, ETH, 18 alts; funding, OI, liquidations, long/short ratio; BTC/ETH options and basis). Not Hermes's full universe.
How: 202 pre-registered cell-horizons in 9 families (PREREG.md below), one shared harness (three periods, Newey-West t, independent episode counts, costs per leg, carry by side). The harness was checked before use: a signal built from future prices passes loudly (t=31), random noise fails, every transform is past-only. One cell passed the mechanical rule; a second agent tried to break it and it broke. The refuter also found a unit bug in the harness's carry term (funding is percent per 8h in the file); it is fixed and the near-miss numbers below are recomputed with the fix and with the tradeable entry timing (lag=1: the file is built about 05:41 UTC the next day, so a live position is taken a day after the signal).

## Bottom line

Nothing on this data survives as a signal at 1 to 10 days. With 202 tests, about 10 passes were expected by chance; 1 passed and did not survive. The four leads below are the only things worth a proper confirmation on Hermes's full universe, and each is weak.

## Near misses, recomputed with correct carry and lag=1 (position taken the day after the signal)

Spread = mean forward return on flagged days minus other days. t = Newey-West t. n = independent episodes. net = after costs and carry.

1. Crowded shorts, BTC (cross-venue OI-weighted funding in its bottom decile -> long BTC)
   h=1: train +0.24% t=0.7 n=38 | val +0.28% t=1.1 n=41 | test +0.07% t=0.2 n=26, net ~0
   h=5: train +0.99% t=0.8 n=26 | val +0.64% t=0.8 n=16 | test +1.95% t=2.3 n=7, net +0.5% val
   Right sign everywhere, never significant once entry is a day late. The Binance-only version and the alt-basket version point the same way at the same weakness. Worth one family-level confirmation; not a trade.
2. Retail long/short ratio at a one-year high -> BTC down
   h=5: train -2.60% t=-2.6 n=16 | val -0.27% t=-0.2 n=12 | test -6.01% t=-3.6 n=8
   h=10: train -4.73% t=-2.6 n=12 | val -0.72% t=-0.4 n=7 | test -8.20% t=-2.6 n=6
   Strong at both ends of the sample, dead in the middle, and 6-16 episodes per period. The large test numbers rest on 6-8 episodes in 2026. Confirm on the full universe (every coin's long/short ratio) before believing it.
3. ETH implied vol at a one-year low (complacency) -> ETH down
   h=5: train -2.23% t=-2.5 n=13 | val -2.38% t=-0.9 n=6 | test -1.41% t=-0.9 n=7
   h=10: train -5.25% t=-3.1 n=8 | val -3.26% t=-1.1 n=5 | test -3.71% t=-1.1 n=6
   Same sign in all three periods at every horizon, but 5-13 episodes each. The BTC version flips sign out of sample, which is a warning. Only a longer history (Laevitas has DVOL from 2021-03; ATM IV from 2019) can settle it.
4. 14-day momentum across the 18 alts (long top 4, short bottom 4)
   h=5: train +0.89% t=2.0 | val +0.67% t=1.6 | test -0.01% t=0.0; net +0.55% val
   Positive in train and validation, flat in 2026, and the full-rank correlation is about zero, so the top-4/bottom-4 result is not supported by the middle of the ranking. Belongs on the 1,600-coin universe, where a cross-section test should be run anyway.

Two reverse-sign patterns appeared and cannot be tested on this file because the sign was read off all three periods: "puts bid" (skew high / risk reversal very negative) was followed by NEGATIVE BTC and ETH returns in train (t about -2 at 10 days), i.e. the options market was right rather than contrarian; and DVOL at a one-year high was followed by negative returns. These are new hypotheses for Hermes to pre-register and confirm on data this pass never touched (2019-2020 options history from Laevitas).

## Clearly dead on this data (do not re-test the same way)
- Options skew / risk reversal as a contrarian signal (0 of 36); funding top decile as a short signal (crowded longs kept going up, 1 of 20 right sign); liquidation spikes as a bounce (0 of 12, no long/short split); open interest extremes (0 of 20; the 2026 "OI high -> down" numbers rest on 1-6 episodes); basis extremes (0 of 20; basis never hit its top decile in validation); long/short ratio bottom decile (0 of 8); dispersion/breadth (0 of 8); 1- and 3-day reversal, funding rank, OI build and liquidation rank across the 18 alts (0 of 15; the 1-day reversal has a real rank correlation of +0.04, t=3, that 60 bps of round-trip cost more than wipes out).

## For Hermes: what to pre-register and confirm on the full universe, in this order
P1. Crowded-shorts family: funding (Binance, OI-weighted cross-venue, z30 <= -2) in its bottom decile -> long, BTC, ETH and the alt cross-section, horizons 3 and 5, lag=1, carry charged, with a market-drift control (compare against the unconditional mean of the same period, and report the spread with BTC's own return subtracted for alts).
P2. Long/short ratio top decile -> short, per coin on the Laevitas panel (ls_ratio_level pct365 >= 0.9), horizons 5 and 10, lag=1.
P3. ETH and BTC DVOL / ATM IV bottom decile -> short, on the 2019-2026 Laevitas history (backfill from L9 first), horizons 5 and 10.
P4. "Puts bid -> down" and "DVOL top -> down" as new hypotheses, confirmed only on 2019-2020 data (never touched here) plus the 2026 test period.
P5. 14-day cross-sectional momentum on the survivor-free universe, horizon 5, weekly rebalance, costs per leg, with the rank-IC reported beside the top/bottom spread.
Everything else in PREREG.md below is dead at these horizons on this data and should not be re-run with nearby thresholds.

---

# Agent synthesis (pre-fix nets; verdicts unaffected)

## Headline

All 202 pre-registered cell-horizons across 9 families were scored on the dashboard file (2020-01-21 to 2026-11-17); exactly 1 passed the pre-registered rule (F3, cross-venue OI-weighted BTC funding in its bottom decile, 1-day horizon), and it was downgraded to fragile under refutation, so 0 survived cleanly. The pre-registration predicted about 10 passes by luck alone; getting 1, which halves when you enter a day late and leans on its best 1-3 validation days, is worse than chance, and the 10 or so cells that did clear the validation t-bar are the predicted noise (they fail on sign, on episode count, or rest on 1-5 flagged days).

Reading guide for the numbers below: "spread" is the average forward return on flagged days minus all other days (in percent); "t" is how many standard errors that spread is from zero (2 is the bar); "n_ind" is the number of independent episodes, where consecutive flagged days count once (30 is the bar). Train is to 2024-06-30, validation 2024-07-01 to 2025-12-31, test 2026-01-01 to 2026-11-17.

## What survived

Nothing survived cleanly. One cell passed the mechanical rule and failed refutation.

| family | cell | horizon | train / val / test spread (t) | n_ind (train+val) | val net | refutation verdict | hypothesis sign matched? |
|---|---|---|---|---|---|---|---|
| F3 Funding extremes | oiw_funding_btc pct365 bottom (BTC, cross-venue OI-weighted funding in bottom 10% of trailing year = crowded shorts) | 1 day | +0.43% (1.0) / +0.51% (2.3) / +0.23% (0.7) | 79 (38+41; 64/68 overlapping flagged days) | +0.09% (unreliable, see carry bug) | FRAGILE. lag=1: val falls to +0.28% t 1.1, net turns negative (-0.43%), hit rate 0.62 to 0.54. Thresholds 0.05 / 0.15: val t 1.5 / 1.5, neither passes. Train from 2022: passes, but validation is identical by construction. Drop the single best validation day: t 2.02; drop best 3: t 1.41; drop best 5: t 0.95. No lookahead found (series lags Binance funding by a day). | yes (+) |
| F3 (robustness row) | same cell, train from 2022-01-01 | 1 day | +0.48% (0.9) / +0.51% (2.3) / +0.23% (0.7) | 63 (22+41) | same | Not an independent pass: identical validation and test rows to the digit. Shows only that 2020-21 did not create the train sign. | yes (+) |

Why fragile matters here: the panel row for day t is built at about 05:41 UTC on t+1, so a live entry sits between lag 0 and lag 1. The lag=1 numbers (val t 1.1, negative net) are the honest lower bound for what a real trade would see. Its sister cell on Binance-only funding (btc_funding bottom h=1: +0.61% / +0.31% t 1.1 / +0.33%) points the same way but never clears the bar, and the two series correlate 0.73, so this is one weak signal seen twice, not two confirmations.

## Near misses worth a proper confirmation

Ordered by how much they deserve another look. None of these is a signal; each is a specific hypothesis Hermes can confirm or kill on the full universe.

1. **F3 "crowded shorts" family (funding bottom decile -> positive), BTC/ETH/alts.** The most consistent thing in the whole pass: 16 of 20 bottom-decile cell-horizons are positive in all three periods, and 20 of 20 are positive in validation. Specific rows: oiw_funding_btc bottom h=3 (+0.23% / +0.74% t 1.6 / +1.08% t 1.7, n_ind 59), h=5 (+1.21% / +1.14% t 1.5 / +1.43% t 1.6, n_ind 42); alt_funding bottom h=3 (+1.71% / +1.81% t 1.8 / +0.07%, n_ind 39, val net positive); btc_funding z30 <= -2 h=10 (+2.32% / +2.93% t 2.0 / +1.51%, n_ind 34). Every one is signed right and every one is a bit too weak. That pattern (consistent sign, t 1.5-2) is exactly what a small real effect looks like, and also exactly what a mild bull-market drift looks like when you are mostly long. Confirmation must control for the drift.
2. **F7 lsr_BTC top decile (retail long/short ratio at a one-year high -> negative).** Same (negative) sign in all three periods at every horizon; train t -2.0 to -2.9; test t -2.9 at h=5 (-5.25%) and -2.6 at h=10 (-7.66%); but validation is flat (-0.15% to -1.04%, |t| 0.2 to 0.8) and n_ind is 28 at h=5, 19 at h=10. lsr_ETH top h=1 and h=10 agree on sign (test t -1.9, -2.1). Strong at both ends of the sample, dead in the middle; the full universe decides.
3. **F2 dvol_eth bottom decile (implied vol at a one-year low = complacency -> negative).** The only F2 cell with the hypothesised sign in all three periods at all four horizons: train t -2.4 to -3.2, validation -0.8 to -1.1 on only 19 flagged days (8-9 episodes), test -0.5 to -1.1. The BTC version has the same train sign (t -2.1 to -2.6) and then flips positive in validation and test, which is a warning.
4. **F9 xs_mom14 (14-day alt momentum, long top 4 / short bottom 4 of 18 coins).** The only cross-section cell with the same sign (positive) in all three periods at every horizon: val t 1.46 / 1.19 / 1.48, train t 2.1 / 2.2 at h=3/5. Caveat that could kill it: the full-rank correlation (IC) is negative in train (t -3.4 at h=1), so the extremes and the middle of the ranking disagree. Needs the larger universe, which is where a cross-section test belongs anyway.
5. **F1 skew_btc chg7 z90 top (BTC put skew rising fast -> positive), h=1.** Positive in all three periods, test t 2.2, but val t 0.8, val net negative, 27 episodes. Lowest priority of the five.

Two reverse-sign patterns were visible but cannot be tested on this file because the sign was read off all three periods (no out-of-sample is left): F1 "puts bid" cells (skew top / risk reversal bottom) are negative rather than positive in train for both BTC and ETH (train t -2.1 / -2.2 at h=10) and negative in all three periods for rr_btc bottom h=1-5, skew_eth top h=3-10, rr_eth bottom h=1-10; and F2 "DVOL top" is negative in train for both assets. If Hermes wants them, they go in as new pre-registered hypotheses ("puts bid -> negative", i.e. the options market is right, not contrarian) and get confirmed only on data this pass never touched.

## What is clearly dead

- **F1 Options skew / risk reversal, contrarian ("puts bid -> up, calls bid -> down"):** 0 of 36. The "puts bid" half has the opposite sign in train for both assets; the "calls bid" half cannot be evaluated because validation holds 1-5 flagged days (the t of 9.0 on skew_btc bottom h=5 is one episode). Skew and risk reversal are -0.94 correlated, so the 8 pct365 cells were really 4 tests.
- **F2 Implied-minus-realized vol and DVOL top ("fear and capitulation -> up"):** 0 of 32. DVOL top has the wrong sign in train for both assets and BTC DVOL never hit its top decile in the entire validation window; vrp_btc top rests on 2 validation days; vrp_eth has no train period at all (realized vol for ETH starts 2024-10). Only dvol_eth bottom is alive (see near misses).
- **F3 "crowded longs" half (funding top decile -> negative):** 1 of 20 cell-horizons signed as hypothesised; btc_funding z30 top h=1 and h=3 are significantly positive in validation (t 2.2, 2.6), i.e. crowded longs went up. Dead. (The bottom half survives as a near miss, above.)
- **F4 Liquidations ("extreme liquidations -> bounce"):** 0 of 12. Validation is positive at 11 of 12 horizons but never reaches |t| 2, the test period flips negative at 10 of 12, and net is negative at every horizon. Without the long/short split this is a coin flip on direction, as the pre-registration warned.
- **F5 Open interest ("OI at a one-year high -> down; OI flush -> up"):** 0 of 20. OI top has the opposite sign in train; the large negative test spreads (oi_BTC top h=3 -2.29% t -6.5) rest on 1-6 episodes in 2026 only. OI flush cells have 9-14 episodes total. btc_oi_share top shows alts outperforming, not underperforming, at h=1-5. oi_ETH top never fired in 2026.
- **F6 Basis ("high basis -> down; low basis -> up"):** 0 of 20. Basis top never fired in validation for either asset (unevaluable). Basis bottom has the opposite sign in train, strongly for ETH (h=10 -7.55% t -3.0), then does not persist. The basis-collapse cell clears t in validation (h=5 t 2.5) but is negative in train and test.
- **F7 "crowded shorts" half (LSR bottom decile -> positive):** 0 of 8 with no consistent sign in any period. Dead. (The top-decile half is a near miss.)
- **F8 Breadth / dispersion ("high dispersion -> BTC down; low dispersion -> alts up"):** 0 of 8. Wrong sign in train at every horizon for the BTC cell (+0.34% to +2.18%), right sign only in test, and 2-5 validation episodes. The alt cell has no consistent sign.
- **F9 1- and 3-day reversal, funding, OI build, liquidations (cross-section):** 0 of 15. Reversal spreads are near zero in train and validation and negative in test (xs_rev3 h=1 test t -2.0) even though the rank IC is positive and significant, so reversal exists in the middle of the ranking but not in the top-4/bottom-4 trade. xs_fund is significantly negative in train at h=5 (t -2.6, opposite sign) and positive in validation and negative in test; xs_oi7 never leaves zero; xs_liq flips sign.

## Data limits of this pass

- **Cross-section is 18 alts only**, and only 7 of them have prices in mid-2020, 14 in 2021-22, all 18 from 2023-05. The harness drops days with fewer than 10 coins, so early train is excluded for every F9 cell. Top 4 / bottom 4 of 18 is a thin portfolio.
- **Options series (skew, risk reversal, DVOL, basis) start 2021-01 to 2021-03**, and the trailing-365 percentile needs 180 observations, so the first signal is mid-to-late 2021. Effective train is about 3 years, not 4.4, and the 2020 cycle is absent. ETH realized vol starts 2024-10, so ETH implied-minus-realized has no train at all.
- **Open interest, liquidations and alt funding start 2022-07 to 2022-10**, giving the F4/F5 cells 15-19 months of train signal and 9-29 independent episodes at longer horizons. Most F4/F5/F6 "insufficient" verdicts are this, not evidence either way.
- **Test period is 10.5 months (2026-01-01 to 2026-11-17, 320 days)**. Several test-period t-stats above 2 rest on 1-6 episodes and should be read as "sign only".
- **No long/short liquidation split**, so F4 cannot condition on which side was liquidated; direction is guessed from the price move.
- **The validation window (2024-07 to 2025-12) was one-sided**: BTC DVOL never reached its top decile, basis never reached its top decile for either asset, and "calls bid" skew/RR extremes fired on 1-5 days. Six cells across F1, F2 and F6 are unevaluable for that reason alone; a different 18 months would have tested different hypotheses.
- **Funding unit bug in the harness** (not fixed, as instructed): every funding column is in percent per 8 hours (31.8% of BTC days are exactly 0.01, the Binance default), but the carry term treats them as fractions, so carry and therefore every "net" figure is overstated roughly 100x (e.g. a 10-day BTC hold shows 25-39% carry). No verdict in this pass was decided by the net check, so no verdict changes, but every val_net above is meaningless and the net criterion will be decisive once something reaches it. Fix before the next run.
- **Near-duplicate series**: skew/rr are -0.94 correlated, btc_funding/oiw_funding_btc 0.73 (median ratio 1.04), so 202 cells are fewer independent tests than they look, and the "10 by chance" figure is if anything generous to the data.
- **Clustering**: flagged days come in runs (skew_btc top: 159 validation flags in 11-34 clusters), so most cells fall below 30 episodes at h >= 5 regardless of how good the signal is.

## Recommendation

Do first, before any new scoring: fix the carry unit (divide funding by 100 or declare it as percent), then re-read the F3 nets. Also fix the live-data alignment so lag=1 is the primary specification; lag=0 is not tradeable on a 05:41 UTC refresh.

What Hermes should pre-register and confirm on the full universe, in this order:

1. **Crowded shorts (funding bottom decile) -> positive forward return**, as one family: cross-venue OI-weighted funding, Binance funding, z30 <= -2, horizons 1/3/5, BTC and ETH and the alt basket, lag=1, and a drift-adjusted spread (flagged minus unflagged within the same month, or a market-neutral version). Pass bar unchanged. If it fails under lag=1 on more venues and assets, the whole F3 story is a bull-drift artefact and gets closed.
2. **Retail long/short ratio top decile -> negative**, BTC and ETH, h=3/5/10, on every venue that publishes it. Train and test agree, validation does not; more assets break the tie.
3. **DVOL bottom decile (complacency) -> negative**, ETH first, then any other asset with an implied vol index. The BTC flip in validation and test is the thing to explain or accept.
4. **14-day alt momentum, cross-section**, on the widest universe available, long top decile / short bottom decile rather than 4 names, and report both the spread and the rank IC. If the IC and the spread still disagree, drop it.
5. **New reverse hypotheses, pre-registered as such**: "puts bid (skew top / RR bottom) -> negative" and "DVOL top -> negative" (the options market is informative, not contrarian). These were seen in all three periods of this file, so only fresh assets or venues count as evidence.

Do not bother with: F1 contrarian skew/RR as written; F2 implied-minus-realized vol and DVOL-top capitulation; F3 crowded-long funding; F4 liquidation bounces until a long/short split exists; F5 open interest in any form on this history; F6 basis until a validation window actually contains a basis extreme; F8 dispersion; F9 1- and 3-day reversal in top-4/bottom-4 form, funding, OI build and liquidation cross-sections. Each of these has either the wrong sign where there is enough data, or no data where it would matter.

Bottom line for the owner: this pass tested 202 specific, written-down bets and the data said no to all of them at the pre-registered standard. That is the correct outcome of a process that works, not a failure of the process. The one pass is a candidate at most, worth one confirmation run, and should be assumed to be noise until the full universe says otherwise.

---

# Pre-registration, 2026-11-18, written before any cell was scored

Data: the public dashboard file (daily, 2020-01-21 to 2026-11-17). Harness: harness.py, rules fixed there.
Periods: train to 2024-06-30, validation 2024-07-01 to 2025-12-31, test from 2026-01-01.
Horizons: 1, 3, 5, 10 days for BTC/ETH events; 1, 3, 5 for the alt cross-section.
Thresholds: trailing-365-day percentile >= 0.9 ("top") or <= 0.1 ("bottom"); z-score >= 2 / <= -2 where stated.
Pass rule: same sign of the spread in all three periods; validation |t_nw| >= 2; test spread same sign; at least 30
independent episodes across train and validation; validation net > 0 after costs and carry. Anything else is
insufficient or rejected. A PASS here is a candidate for Hermes to confirm on the full universe, not a signal.

Nothing outside this list is scored. If an agent scores something else, it is labelled exploratory and does not count.
Total pre-registered cells: 9 families, 46 event cells x 4 horizons + 6 cross-section cells x 3 horizons = 202 cells.
With 202 cells, about 10 would pass a |t|>=2 validation bar by chance alone. A family is interesting only if several
related cells pass together and the sign matches the hypothesis.

## F1. Options: skew and risk reversal (BTC and ETH)
Hypothesis: when puts are unusually bid (skew high / risk reversal very negative), fear is priced and near-term returns are positive; when calls are bid, negative.
- skew_btc pct365 top -> expect positive forward BTC return; skew_btc pct365 bottom -> negative
- rr_btc pct365 bottom -> positive; rr_btc pct365 top -> negative
- skew_eth pct365 top / bottom; rr_eth pct365 bottom / top (ETH returns)
- skew_btc chg7 z90 top (skew rising fast) -> positive

## F2. Options: implied minus realized vol, DVOL level
Hypothesis: a large implied-realized premium (fear) precedes positive returns; DVOL at a one-year high marks capitulation.
- vrp_btc = dvol_btc - rv_btc, pct365 top -> positive; bottom -> negative
- dvol_btc pct365 top -> positive (contrarian); dvol_btc pct365 bottom (complacency) -> negative
- vrp_eth, dvol_eth same

## F3. Funding extremes (reversal)
Hypothesis: crowded longs (funding top decile) precede negative returns; crowded shorts precede positive.
- btc_funding pct365 top -> negative; bottom -> positive
- eth_funding pct365 top / bottom
- oiw_funding_btc pct365 top / bottom (cross-venue, OI-weighted)
- alt_funding pct365 top / bottom (on alt_price, the 20-name basket)
- btc_funding z30 >= 2 -> negative; <= -2 -> positive

## F4. Liquidations (cascade reversal)
Hypothesis: a day of extreme liquidations marks forced selling and precedes a bounce (1-5 days).
- liq_BTC pct365 top -> positive; liq_ETH pct365 top -> positive
- liq_BTC pchg7 z90 top (liquidations surging) -> positive
Note: the long/short split is not in the file, so direction is inferred from the price move; this is a weaker test.

## F5. Open interest
Hypothesis: open interest at a one-year high with price up is crowding (negative); a sharp OI drop is a flush (positive).
- oi_BTC pct365 top -> negative; oi_BTC pchg7 z90 bottom (flush) -> positive
- oi_ETH same
- btc_oi_share pct365 top (capital rotating to BTC) -> alts underperform: tested as alt_price event, negative

## F6. Basis and term structure
Hypothesis: basis at a one-year high is leveraged-long crowding (negative over 5-10 days); very low or negative basis is washed-out (positive).
- basis_btc pct365 top -> negative; bottom -> positive
- basis_eth same
- basis_btc chg7 z90 bottom (basis collapsing) -> positive

## F7. Long/short ratio
Hypothesis: retail long/short ratio at an extreme is contrarian.
- lsr_BTC pct365 top -> negative; bottom -> positive
- lsr_ETH same

## F8. Breadth and dispersion
Hypothesis: when few alts hold their trend (dispersion high) risk is off and BTC underperforms over 5-10 days; dispersion low precedes alt rallies.
- dispersion_14 pct365 top -> BTC negative; bottom -> alt_price positive

## F9. Alt cross-section (18 coins, long top 4 short bottom 4)
Hypothesis: short-term reversal (last 1-3 day losers outperform), funding extremes reverse, OI builds are crowding.
- xs_rev1: signal = -(1-day return); xs_rev3: -(3-day return) -> expect positive spread (reversal)
- xs_mom14: 14-day return -> momentum, sign unknown; reported as is
- xs_fund: -(funding pct365) -> crowded longs underperform -> positive spread
- xs_oi7: -(OI 7-day % change) -> OI builds underperform -> positive spread
- xs_liq: liquidations pct365 -> bounce -> positive spread

## Robustness, applied to anything that passes
1. lag=1 (take the position a day later): must keep sign and most of the spread.
2. Threshold neighbours 0.85/0.95 (or 0.05/0.15): must keep sign.
3. Exclude 2020-2021 from train: must keep sign.
4. Overlapping-window count vs independent episodes: report both.
A pass that fails any of these is downgraded to "fragile".
