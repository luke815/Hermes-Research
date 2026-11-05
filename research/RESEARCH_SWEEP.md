# Research sweep engine: breadth in code, judgment in the model

This adds a continuously running sweep to the research loop. The sweep tests every cell of the search space on the train period, in code, around the clock, and maintains a leaderboard. The scheduled model runs no longer invent and test one candidate each; they read the leaderboard, pre-register survivors, confirm them on validation and test under a bar that rises with the number of cells swept, and write verdicts. RESEARCH_PROGRAM.md, the cycle addendum and RESEARCH_LOOP.md still define targets, periods, costs, episode counting and reporting. This document defines how breadth is achieved without overfitting.

## 1. Division of labour
- The sweep (scripts/sweep_daemon.py, a tracked background process with a heartbeat, like the board daemon): computes indicators and factors, builds cells, scores each cell on the train period only, writes results to results/sweeps/, maintains the leaderboard, never touches validation or test, never changes the live score or the dashboard contract.
- Model runs (every two hours, lock-protected, twelve a day): read the leaderboard, pick the top unconfirmed survivors, pre-register them, run the confirmation on validation and test, write the verdict, push, post three lines. When nothing is waiting, they do generator work from RESEARCH_LOOP.md section 3, propose new search-space dimensions for the sweep, or run disproof tests on admitted factors.
- The weekly run is the only one that changes the live score, the setup library, the strategy library or the dashboard contract.

## 2. The indicator and factor library
Install pandas-ta (or the ta package if pandas-ta fails to build) and expose every indicator it provides through one function, indicators(frame) -> frame, on daily, 4-hour and hourly bars. Add the custom ones that are not in it: TD Sequential setups and countdowns, Pi cycle, Mayer multiple, the weekly 20 SMA and 21 EMA band, funding persistence counts, OI-on-down-days, liquidation cascade flags, breadth series across the universe, cross-venue funding dispersion, and every factor family in the two programs. Each indicator carries metadata: family, inputs needed, minimum history, and whether it is level, oscillator, flag or count. The library is a module in the repo with tests; the sweep imports it.

## 3. The search space, as cells
A cell is one tuple. The sweep enumerates them from the library and the metadata.
- Measure: any indicator or factor in the library.
- Transform: raw; 1-year percentile; z-score 30 or 90; change 3, 7, 30; persistence (bars beyond a percentile); acceleration; divergence from price over 20 bars; cross-sectional rank; ratio to BTC's own value; crossover flags for pairs that make sense (price and average, fast and slow average, oscillator and its signal).
- Direction and threshold: above or below the 80th, 90th, 95th percentile, or 20th, 10th, 5th; crossovers as events.
- Target: forward return 1, 3, 10 bars; relative return against BTC; top event T(30, 20) and bottom event B(30, 20, 7) on candidate days, as amended; hourly and 4-hour bar versions with horizons 4, 12, 24 bars.
- Universe: BTC; ETH; pooled majors; full point-in-time cross-section (from D1).
- Conditioning: none; heat tercile; realized-vol tercile; trend state; one admitted factor's extreme (section 6).
- Timeframe: daily, 4-hour, hourly where data exists.

Cells that cannot meet the minimum history or minimum episode count on train are skipped and counted as skipped, not tested. The enumeration is written to results/sweeps/space.json so the count of cells is known and the deflated bar in section 5 can be computed.

## 4. Scoring a cell on train
For every cell, on the train period only, net of the costs table, with features lagged one bar and percentiles from past data only:
- Return targets: mean net return in the signalled state against the unsignalled state, independent n (non-overlapping), Newey-West t, rank IC where the cell is cross-sectional, per-year sign table.
- Event targets: lift against the base rate among candidate days, episode count, episode-bootstrap 90 percent interval, lead time, false-alarm rate.
- Stability: the score at the two neighbouring thresholds and the two neighbouring lookbacks; a cell is marked fragile if the sign changes at a neighbour.
- Novelty: correlation of the cell's signal with every admitted factor at the same target; above 0.7 marks it as a duplicate.
Everything is written as one row per cell to results/sweeps/<date>.parquet (cell id, all statistics, train period hash, library version). The leaderboard, results/sweeps/leaderboard.json, ranks the cells that are not fragile and not duplicates by a single train score (t-stat for return targets, bootstrap lower bound of lift for event targets), per target family, and lists the top 50 of each with the count of cells enumerated and tested so far.

## 5. Confirmation and the deflated bar
Validation and test are never read by the sweep. A model run confirms a leaderboard survivor like this:
- Pre-register: cell id, hypothesis, the rule as enumerated, horizon, universe, pass criterion, and the number of cells tested in that target family so far, N.
- The bar scales with N. For return targets, the validation t-stat must exceed the deflated threshold 2 + 0.5 log10(N) (so 2.5 at ten cells, 3.0 at a hundred, 3.5 at a thousand, 4.0 at ten thousand), with the same sign as train. For event targets, the validation bootstrap lower bound of lift must exceed 1 and the episode count must meet the amended bar; the lift itself must exceed 1 + 0.1 log10(N).
- The test period is reported and gates once it holds the minimum episodes or 40 independent return observations; before that an admitted cell is "test pending".
- One confirmation attempt per cell, ever. A cell that fails in validation is closed; its neighbours are not tried as a way around it.
- Survivors carry their N in the results file and on the dashboard, next to their statistics, so the breadth of the search that produced them is always visible.

## 6. Combination layer
After single cells, the sweep tests conjunctions of two admitted or validation-passed cells at the same target (both signalled), and the conditioning of one by another (cell A scored only when cell B is in its state). These are cells too, enumerated from the survivor list, counted in N, and confirmed the same way. No more than two conditions per rule; three-condition rules are overfitting by construction at this sample size.

## 7. Timeframes and data the sweep needs
- Daily: the full panel, the cross-section from D1, the delisted names, the breadth series.
- 4-hour and hourly: the incremental intraday store from the board daemon, extended to the top 100 names and to 2 years where Coinalyze serves it, pulled by the same token-bucket rules.
- The sweep recomputes indicators only for the bars that changed since its last pass; a full recompute happens weekly or when the library version changes.

## 8. Cadence and budget
- The sweep runs as a background process with a heartbeat; the hourly health job restarts it if the heartbeat is over 90 minutes old. It paces itself so the daily refresh and the board daemon always have the API budget they need; the sweep never calls the API itself, it reads the stores.
- Model runs every two hours, lock-protected, each bounded to one confirmation or one generator task. Twelve a day. If the leaderboard has no unconfirmed survivor, the run writes "nothing to confirm" and does generator or disproof work.
- The weekly run reports: cells enumerated, tested, skipped, fragile, duplicate; survivors by target family; confirmations attempted and passed; the current deflated threshold per family; the admitted list and the strategy library with live statistics.

## 9. What reaches the trading layer
An admitted cell becomes, automatically and in this order: a row in the setup library with its full record; a strategy test in strategy.py with the twelve variants; a live entry in the ideas list when it fires, with its tier; a paper-traded row in the ledger. Nothing reaches the ideas list from the sweep directly. The path is sweep, confirm, strategy, ideas, and every step is on the dashboard.

## 10. Dashboard keys
data.json gains sweep: { as_of, cells_enumerated, cells_tested, cells_skipped, fragile, duplicates, by_family: [ { family, tested, survivors, threshold_now } ], leaderboard: [ { cell_id, family, rule, target, universe, train_score, train_n, status } ] (top 20 per family), confirmations: [ { cell_id, date, validation, test, verdict } ] (last 30) }. The page will show it as a sweep panel; until then the key is written anyway.

## 11. Why this is still honest
Breadth is the enemy of validity unless the bar rises with the breadth. This design keeps validation and test untouched by the search, counts every cell tried, raises the confirmation bar with that count, forbids retrying neighbours of a failed cell, and limits conjunctions to two conditions. A survivor of this process has been found by a broad search and confirmed by a narrow one, which is the only combination that produces signals worth trading. Luke's direct instruction overrides this document; the hard limits are unchanged.
