# Sweep v2: throughput, the derivatives family, and what admitted means

## 1. Throughput: vectorize the scorer
At 69 cells an hour a pass over the cross-section takes two months. The cause is per-cell recomputation. The fix is to compute once per measure and evaluate every cell of that measure as matrix operations.

Design, per universe and timeframe:
- Load the panel as matrices, dates by names: close, high, low, volume, funding, open interest, and the derivatives series where they exist. Forward return matrices R_h for h in 1, 3, 10 and their relative-to-BTC versions, computed once and cached to disk with the panel hash.
- Candidate-day masks and episode ids for the event targets, computed once from the amended definitions and cached.
- For each measure: one indicator matrix M (dates by names), computed by the library across all names at once.
- For each transform: one matrix T from M using rolling, past-only operations (rolling percentile over 252, rolling z over 30 and 90, shifts for change and acceleration, rank across the name axis for xs_rank, 20-bar divergence against price). Twelve matrices per measure.
- For each threshold and direction: a boolean signal matrix S from T. For percentile transforms the threshold is the per-name rolling percentile; for xs_rank it is the per-date cross-sectional quantile.
- Return targets: per date, mean of R_h where S is true minus where false, giving a daily spread series; rank IC per date between T and R_h across names. Non-overlapping t-stat, Newey-West t, per-year sign table from those series. Event targets: lift as the event rate under S on candidate days divided by the base rate on candidate days; episode bootstrap by resampling episode ids, 1,000 draws, vectorized.
- Fragility and novelty from the same matrices: the neighbouring thresholds are adjacent quantile cuts of the same T; correlation with admitted factors is a correlation between T and the stored admitted matrices.
- Write one row per cell in batches; checkpoint after each measure; a measure whose rows exist for the current panel hash is skipped.
- Multiprocessing by measure across the box's cores, each worker writing its own part file, merged by the leaderboard job.

Correctness gate before it replaces the old scorer: on 50 randomly chosen cells the vectorized statistics match the per-cell scorer to six decimals, and the lookahead test (perturb all data after day t, assert no cell's signal at t changes) passes. Both tests live in tests/.

Target: at least 5,000 cells an hour per process on the daily cross-section, so a full pass of the current space completes inside a day, and intraday cells become affordable when D4 lands. Report cells per hour from the first full hour and after each library change.

## 2. The derivatives family from Laevitas
The indicator library is 47 measures, almost all price-based. The derivatives and options data the box already pulls, or can pull from the same source, is a separate family and goes in as measures with the same metadata, so every one of them enters the sweep with every transform and target.

Market level, BTC and ETH (SOL where the endpoint serves it)
- DVOL level; DVOL 7-day change; DVOL minus 30-day realized vol (the variance risk premium); DVOL percentile against its own year.
- ATM implied vol at 7, 30 and 90 days; the term slope (90-day minus 7-day); inversion flag.
- 25-delta skew at 7, 30 and 90 days; skew change over 5 days; skew term slope; risk reversal; butterfly where served.
- Options open interest and its 7-day change; put-call open interest ratio when get_market_positioning_history recovers (retry weekly, logged).
- Futures basis at 1 week, 1 month and 3 months annualized; the basis curve slope; perp premium against the index; basis percentile.
- OI-weighted cross-venue funding: level, 7-day average, persistence counts, dispersion across venues.
- Total futures open interest against its 90-day high; OI change on down days minus up days; OI flush flag.
- Realized vol 7 and 30 days; their ratio; vol of vol over 30 days.
- Hyperliquid aggregate: funding minus CEX funding; open interest share against CEX.

Per name, for the cross-section (needs D2 and D3 from the data queue, then enters the sweep as cross-sectional measures)
- Funding by venue and the cross-venue spread; Hyperliquid funding minus Binance funding per name.
- Open interest by venue; venue concentration; OI change 1, 7, 30 days; OI against the name's 90-day high.
- Basis per name where listed; perp premium per name.
- Liquidations per name, long and short, as a share of OI, 1 and 3 days (from Coinalyze, already on disk for the 20, extend to the universe).
- Realized vol per name 7 and 30 days and the ratio; vol percentile; vol rank across names.

Each measure carries family "derivatives" or "options", its inputs, minimum history and type, and passes the lookahead test. The sweep's budget counts them as new combinations, which raises the bar accordingly; that is correct.

## 3. What admitted means, stated once
A cell, setup, book rule or risk dial is admitted when all of the following hold, and the result file shows each:
1. Pre-registered before any out-of-sample number was computed.
2. Sign and size hold in validation and in test separately (test gating once it has the minimum observations), under the deflated bar for its family's distinct-combination count.
3. Per-year sign consistent in at least four of the six calendar years since 2020, and no single year supplying more than half of the effect.
4. Net of the costs table at the tier the names actually trade in, with funding carry.
5. Stable at both neighbouring thresholds and both neighbouring lookbacks.
6. Not a duplicate: correlation below 0.7 with every admitted signal at the same target.
7. Survives one disproof test chosen after admission: a different period split, a harsher cost tier, or the other side of the universe by liquidity.
8. Four weeks of paper track inside the backtest's bootstrap interval before it is called live.
Anything short of this is provisional, watch, insufficient or rejected, and is labelled so on the page. This is the entire meaning of "bulletproof" that six years of data can support.

## 4. Queue insertion
- S7. Vectorized scorer with the correctness gate and multiprocessing; the old scorer retired. Two runs. Nothing in the research queue runs ahead of it, because every later item depends on the pass finishing.
- S8. The derivatives and options family in the library, market level, with tests; cells re-enumerated; one run.
- D2 and D3 pulled through the resumable puller; then the per-name derivatives measures; two runs.
- The bottom scorecard (C2, C3, C4 per name on the pooled panel) immediately after S7, since it shares the event matrices.
- Then R1 to R6, B3, B4, D4, and the generator.
