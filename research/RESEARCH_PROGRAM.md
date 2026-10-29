# Research program v2: from regime read to trade ideas

This replaces the research sections of MANDATE.md. The regime score, the discipline rules, the single-writer rule and verify-before-report stay. What changes is the target: the output of this system is a daily list of names that look ready for a run or a short, each backed by an event study on the full history, scored live, and shown on the dashboard. The BTC level forecast is demoted to context.

## Why the direction changes
Every retest so far says the same thing: the factors that survive are momentum and volatility, the BTC level forecast is not reliable outside the hot zone, and the alt-basket spreads are two to three times the BTC spreads for every factor. The edge, if there is one, is in choosing which names, not in calling the BTC level. So the model becomes cross-sectional and event-driven, and the regime score becomes the gate.

## 1. Universe and data

- Universe: every perp with at least 20m USD open interest or 10m USD daily volume on Binance, Bybit, OKX or Hyperliquid, rebuilt daily, and recorded point in time. A name is in the backtest universe on a date only if it met the threshold on that date. Today's top 50 applied to 2021 is survivorship bias and is a FAIL.
- Per-asset daily panel: close, high, low, volume, open interest, funding (close and average), liquidations long and short, long/short ratio, basis where listed, from Coinalyze for the 20 historical names and from Laevitas for the rest. Record the first date each series exists.
- Per-asset 4-hour panel for the top 30 by OI, from Laevitas per-instrument endpoints, for the 1 to 3 day horizon. Accept shorter history and test it separately.
- Market panel: BTC and ETH everything already on disk, plus total alt OI, total stablecoin supply if a free source exists, and the heat score.
- Costs table: taker fee and a slippage assumption per venue tier (5 bps fee plus 10 bps slippage for liquid names, 25 bps slippage below 50m OI), and funding carry accrued while a position is held. Every backtest return is reported net of these.

## 2. Feature families, per asset, per day
Compute each as a raw value, a 1-year percentile for that asset, and a cross-sectional rank across the universe that day. Shift everything by one bar before use.

Price structure
- Returns 1d, 3d, 7d, 14d, 30d, 90d; the same relative to BTC (relative strength).
- Distance from 20, 50, 200-day averages in ATR units; slope of each over 10 days.
- Position in 20-day and 55-day range (0 at low, 1 at high); days since 20-day high and low.
- Donchian breakout flags; close above prior 20-day high on volume above its 20-day median.
- Drawdown from 90-day high; days since.

Volatility
- Realized vol 7d and 30d, their ratio, 1-year percentile of 30d vol.
- Bollinger width 20d and its 6-month percentile (squeeze when below the 15th percentile).
- ATR 14 as percent of price; ATR regime (ATR 14 over ATR 100).

Positioning
- Funding close, 3d and 7d average, 30d z-score, 1-year percentile; count of consecutive days above the 80th or below the 20th percentile.
- Open interest change 1d, 3d, 7d, 30d; OI as percent of its 90-day high; OI in USD divided by 30-day average volume (crowding).
- OI change on down days versus up days over 7 days (who is adding).
- Liquidations: long and short liquidations as percent of OI, 1d and 3d; cascade flag when 3d long liquidations exceed 5 percent of OI.
- Long/short ratio and its 30d z-score.
- Basis and perp premium where listed; cross-venue funding dispersion; Hyperliquid funding minus CEX funding.

Flow and participation
- Volume relative to 30-day median; volume on up days versus down days; volume trend over 10 days.
- OI-weighted price, if OI and price both rise versus diverge.

Market context (same for all names that day)
- Heat score and zone, BTC 7d and 30d return, BTC realized vol percentile, alt-basket breadth (percent of universe above its 20-day average), ETH/BTC 30d return.

## 3. Backtest standard v2
The half-split test stays as a first filter. Nothing reaches the scanner or the dashboard on the half split alone.

- Three periods, fixed now and never moved: train to 2024-06-30, validation 2024-07-01 to 2025-12-31, test 2026-01-01 onward. A result counts only if the sign and rough size hold in validation and test. Report all three. The test period grows every day and is never used to choose parameters.
- Rolling walk-forward for any fitted model: 2-year window, refit monthly, score the next month. Report performance per calendar year, not one pooled number. A model that works in two years out of six is not a model.
- Horizons: 1d, 3d, 10d forward return, reported side by side. A signal is admitted at the horizon where it holds, and used only there.
- Overlap: 10-day labels overlap. t-stats use non-overlapping windows or Newey-West with lag equal to the horizon. State which.
- Cross-sectional metrics, per day: rank information coefficient (Spearman between signal rank and forward return rank), its mean, its t-stat, the hit rate of IC above zero; decile spread top minus bottom; turnover of the top decile; capacity (median OI of top-decile names).
- Event metrics, per setup: number of triggers, mean and median forward return, hit rate, 25th and 75th percentile, worst 10 percent, versus a matched baseline of the same asset on random days in the same heat tercile. Report the difference with a bootstrap 90 percent interval from 2,000 resamples. Fewer than 40 independent triggers means "insufficient", not "promising".
- Costs: every reported return is net of the costs table. Show gross beside it once so the gap is visible.
- Multiple testing: every candidate is pre-registered in research/backlog.md with the hypothesis, the exact rule, the horizon and the pass criterion before any number is computed. The count of candidates tested since the last admission is printed next to every admission. With more than 20 tests, raise the required t-stat to 3.
- Regime conditioning: every result is reported for the full sample and within heat terciles. A long setup that only works in the hot tercile is admitted with that gate attached. A setup whose edge sits entirely in one calendar year is rejected.
- Parameter stability: for any threshold (percentile cut, lookback), show the result at the neighbouring values. An edge that exists at the 80th percentile and vanishes at the 75th and 85th is noise.
- Point-in-time universe, shifted features, no future data in any percentile or z-score window. Percentiles use only past data for that asset.

Every test writes results/<date>_<candidate>.json with all of the above and a one-line verdict: admitted at horizon H with gate G, rejected because R, or insufficient.

## 4. Cross-sectional ranking model
- Target: 10-day forward return relative to BTC, and separately 3-day.
- Candidates for the composite: 14d and 30d relative strength, 7d OI change, funding 7d average (negative sign, crowding penalty), volume trend, 20-day range position, squeeze flag, distance from 50-day in ATR. Test each alone first (section 3), keep what passes, then combine by rank average with equal weights. Learned weights only if they beat equal weights in validation and test, by rolling walk-forward.
- Report: decile spreads, IC series, per-year table, turnover, capacity, and the same within heat terciles. Expectation from the literature: 1 to 4 week cross-sectional momentum is the most robust alt effect, 1-day reversal exists in small names, and crowded funding mean-reverts. Confirm or reject each on this data.
- Output daily: rank, composite score, decile, expected relative return at 3d and 10d from the decile's validation-plus-test history, and the three features driving the rank.

## 5. Setup library
Each setup is a precise rule with a confirmation, an invalidation and a measurement plan. Test each by the event standard in section 3, at 1d, 3d and 10d, full sample and by heat tercile. Thresholds are starting points and must pass the neighbouring-value check.

Longs, names ready for a run
1. Compression breakout. Bollinger width below its 15th percentile for at least 10 of the last 15 days, close today above the 20-day high, volume above 1.5 times its 20-day median, OI up on the day, funding below its 70th percentile. Invalidation: close back inside the range. Expect: continuation over 3 to 10 days, strongest in the neutral and hot terciles.
2. Capitulation reversal. OI down more than 25 percent over 7 days, price down more than 15 percent over 7 days, long liquidations over 3 days above 5 percent of OI, funding below its 20th percentile, then the first close above the prior day's high. Invalidation: close below the capitulation low. Expect: mean reversion over 1 to 3 days, long tail of failures in the cold tercile.
3. Momentum pullback. Relative strength 30d in the top decile, price pulled back to within 1 ATR of the 20-day average, funding fell from above its 80th percentile to below its 50th while price held above the 50-day, OI flat or lower (longs flushed, trend intact). Invalidation: close below the 50-day. Expect: 3 to 10 days.
4. Short squeeze. Funding below its 10th percentile for 3 or more days, OI at or above its 60-day high, price has not made a new 20-day low in the last 5 days, short liquidations rising. Invalidation: new 20-day low. Expect: sharp 1 to 3 day move, lower hit rate, larger average win; size smaller.

Shorts, names that look done
5. Crowded long. Funding above its 90th percentile for 3 or more days, OI at its 90-day high, price has not made a new 20-day high in the last 5 days, relative strength 7d turning negative. Invalidation: new 20-day high. Expect: 3 to 10 days, strongest when heat is falling from the hot zone.
6. Exhaustion. Distance above the 50-day average at a 1-year high in ATR units, 7d return above the 95th percentile of that asset's own history, volume on the last two up days below the prior three, OI flattening while price rises (spot-led blow-off) or OI exploding with price (leverage-led, more violent). Record which; test both. Invalidation: new high on rising OI and volume.
7. Breakdown. Close below the 20-day and 50-day averages, OI rising on down days for 3 of the last 5 days, funding still above its 50th percentile (longs have not given up), relative strength 14d in the bottom quintile. Invalidation: close back above the 20-day. Expect: 3 to 10 days.
8. Failed breakout. Close above the 20-day high two to five days ago, now back below it, OI higher than before the breakout (trapped longs), funding above its 70th percentile. Invalidation: reclaim of the breakout level. Expect: 3 to 10 days.

For every setup record: the trigger count per year, the hit rate and mean net return at each horizon, the baseline, the bootstrap interval, the result by heat tercile, and the result at neighbouring thresholds. Admit only with a verdict line. Keep rejected setups in the library with their numbers so they are not retested without a new angle.

## 6. Regime gate
- Long setups fire in the neutral and hot zones. In the cold zone they are shown as watchlist only, unless their own tercile test says otherwise.
- Short setups fire in all zones, but in the hot zone they require tier A confirmation and are flagged as counter-trend.
- Regime crossings widen or narrow the universe: in the hot zone, the long list may include the second decile; in the cold zone, only the top decile.
- These rules are themselves tested: report every setup's result with and without the gate.

## 7. Daily idea output
Written to data.json under ideas and watchlist, and posted in the digest.

- Each idea: symbol, side, setup name, horizon, composite rank and decile, expected net return and hit rate from the setup's validation-plus-test history with n, the three features that fired with their values, the invalidation level, a confidence tier, the regime gate state, the venue with the best liquidity, and a size hint as a fraction of a unit risk budget scaled by inverse 30-day vol.
- Tier A: setup admitted in validation and test, regime gate open, two independent families confirming (price structure plus positioning, or volatility plus positioning), composite rank in the top or bottom quintile on the matching side. Tier B: one family short of A. Tier C: admitted setup fired but the gate is closed or the rank is mid.
- Watchlist: names within one day of a trigger (compression at the 20th percentile, funding at the 85th, price within 1 percent of a breakout level), so the next move is visible before it fires.
- Tier A alerts go to the home channel at once with one line each. The rest wait for the digest. If nothing qualifies the digest says so.
- Every idea is written to signals/ledger.csv when it fires with the entry reference price, and the realized net return at 1d, 3d and 10d is filled in as the horizon passes. The ledger is the only source of live hit rates.

## 8. Live tracking and decay
- Weekly: live hit rate and mean net return per setup and per tier, against the backtest numbers, with n. A setup whose live result sits below the bottom of its bootstrap interval for eight consecutive weeks is demoted to watch and retested on the expanded history.
- Monthly: full rerun of every admitted setup and the composite on the expanded test period. Per-year table updated. Any sign flip in the newest year is reported first.
- Track turnover of the idea list and the share of ideas that reach invalidation before their horizon.

## 9. Nightly loop and backlog order
Each night the research job takes one item, in this order, pre-registers it, tests it to the section 3 standard, writes the results file, updates the backlog and posts three lines. It does not start the next item until the current one has a verdict. Bounded items only; a build that cannot finish in one session is split.

1. Point-in-time universe and per-asset daily panel, with first-date inventory.
2. Costs table and net-return plumbing in the tester.
3. Three-period split and per-year reporting added to the tester; rerun the four regime factors through it and report.
4. Single-feature cross-sectional tests: relative strength 14d and 30d.
5. Funding 7d average and OI 7d change as cross-sectional signals.
6. 1-day reversal in the bottom half of the universe by OI.
7. Composite ranking, equal weights, decile and IC report, by year and by tercile.
8. Setup 5, crowded long. Then 1, compression breakout. Then 7, breakdown. Then 3, momentum pullback. Then 2, 6, 8, 4.
9. Regime gate test for every admitted setup, with and without.
10. 4-hour panel for the top 30 and the 1 to 3 day versions of setups 2 and 4.
11. Cross-venue and Hyperliquid funding divergence as a confirmation feature.
12. Learned weights for the composite by rolling walk-forward, against equal weights.

## 10. Dashboard additions
data.json gains four keys; the page will be extended to show them.

- ideas: array of the idea objects in section 7, long and short, sorted by tier then score.
- watchlist: array of near-trigger names with the setup, the distance to trigger and the direction.
- setups: replaced by setup_library, an array with name, side, horizon, status (admitted, watch, rejected, insufficient), triggers by year, hit rate, mean net return, baseline, bootstrap interval, result by heat tercile, live n, live hit rate, and the date last retested.
- ranking_stats: IC mean and t-stat, decile spread, turnover and capacity for the composite, by year and by tercile, plus the IC series for the chart.

Until the page is extended, write the keys anyway. Nothing in the contract is removed.

## Hard limits, unchanged
No trades, no spending, no keys in chat, no number without a results file, no claimed edge outside the period and zone where it held, no invented data for an empty section. Luke's direct instruction overrides this document.
