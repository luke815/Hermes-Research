# Research loop: how the system finds its own next test

This closes the gap that makes the research stall between instructions. The backlog stops being a fixed list and becomes a queue the system refills itself, from a defined search space, under a testing budget, with every admitted signal flowing automatically into a strategy backtest. RESEARCH_PROGRAM.md and RESEARCH_PROGRAM_CYCLE.md define how a test is run; this document defines where the next test comes from and what happens after one passes.

## 1. Run cadence
- Research runs at 02:00, 08:00, 14:00 and 20:00 Amsterdam. Each run: take the lock, pick the top queued item, pre-register, test, write the results file, write the verdict, release the lock, push both repositories, post three lines. If the lock is held, exit silently.
- Every run ends by checking the queue depth. Fewer than eight queued items triggers the generator in section 3 before the run ends.
- Independent factor-family items run as parallel subagents inside one run, each writing its own results file; verdicts are serialized through the lock.
- The weekly Sunday run is the only one that may change the live score, the admitted lists or the dashboard contract. The other runs test and record.

## 2. Data expansion queue
New signals need new data more than new transforms. These are infrastructure items and sit at the top of the queue until done, each with a first-date inventory and a verify_panel pass.

- D1. Full perp universe from Coinalyze: every Binance, Bybit and OKX perp, price, volume, funding, open interest, liquidations, long/short, daily, from each name's first bar, including delisted names by symbol. This replaces the fixed 20.
- D2. Per-exchange funding and open interest for the universe (Coinalyze per-market endpoints), so cross-venue divergence is computable per name.
- D3. Hyperliquid per-instrument funding, open interest and price from Laevitas, daily and 4-hour, from December 2024.
- D4. 4-hour bars for the top 30 by open interest, price, funding, open interest, 2 years where available.
- D5. Options for ETH and SOL where Laevitas serves them: DVOL equivalent or ATM IV, skew, risk reversal, and the term structure once the endpoint recovers.
- D6. Free external series, each behind a reachability check and a source note: stablecoin supply and DEX volume (DefiLlama), MVRV and realized price (Coin Metrics community), spot ETF flows (Farside), Fear and Greed, DXY and the US 10-year (FRED or stooq), BTC and NDX correlation inputs.
- D7. Weekly bars derived from daily for every series, with the week closing Sunday 00:00 UTC, for the cycle layer.
- D8. Exchange listing and delisting dates per name, from each name's first and last bar, stored as a table so the point-in-time universe is explicit.

Every expansion item writes its series into the panel under the naming rule in the dashboard spec and into data.json, so it is visible the day it lands.

## 3. Hypothesis generator
When the queue is short, the run produces new candidates from the search space below, scores them, pre-registers the top ones and appends them to the queue. It writes what it generated and why to research/generated.md. Nothing is tested in the same run it is generated.

Search space, one candidate is one cell
- Family: positioning, trend and exhaustion, volatility, breadth, flows and on-chain, options, cross-venue, macro conditioning, TA pattern.
- Measure: any series in the panel for that family.
- Transform: level percentile (1 year), z-score (30 or 90), change (3, 7, 30 bars), persistence (bars in a row beyond a percentile), acceleration (change of change), divergence from price (sign of measure change against sign of price change over 20 bars), cross-sectional rank, ratio to BTC's value.
- Target: forward return at 1, 3 or 10 days; relative return against BTC; top event T(30, 15); bottom event B(30, 15, 7); the weekly versions.
- Universe: BTC, ETH, pooled majors, full cross-section.
- Conditioning: none, heat tercile, realized-vol tercile, trend state (above or below the 200-day).

Scoring a candidate, 0 to 5 each, sum ranks the queue
- Prior: has a documented practitioner or academic basis for this family and target (momentum, crowding, capitulation, breadth extremes score high; arbitrary lookbacks score low).
- Data: the series exists on disk with at least four years or, for cross-section, at least two years and 50 names.
- Novelty: no verdict exists for the same family, transform and target; the measure is not a near-duplicate (correlation above 0.7) of an admitted factor at the same target.
- Reach: the result would change something, a new admitted factor, a gate for a setup, a new data source confirmed useful, or a rejected family closed for good.
- Cost: fits in one run on existing modules (high) or needs new code or a pull (low).

Rules
- Rejected cells are never regenerated without a different transform or target, and the log says which earlier verdict they extend.
- The generator may not change thresholds, horizons or periods to rescue a result. Those are fixed in the programs.
- Generated candidates carry the pre-registration text in full: hypothesis, exact rule, horizon, pass criterion, expected independent n. A candidate with an expected n below 40 is marked "insufficient by design" and queued only for the pooled universe or the cross-section.
- Once a week the generator also proposes two "disproof" candidates: tests designed to break an admitted factor (a different period, a different asset, a harsher cost tier). Surviving disproof is how a factor earns a higher tier.

## 4. Testing budget
- A running count of tests since the last admission is printed in every verdict. Below 10 tests, the pass bar is t above 2 in validation and test with the same sign; from 10 to 20, t above 2.5; above 20, t above 3. The count resets on an admission.
- Every Sunday the run reports the week's test count, admissions, and the implied false discovery rate at the current bar, in plain words.
- An admitted factor goes to the live score, a setup or a strategy only after surviving one disproof candidate.

## 5. Strategy backtester
Every admitted signal is a strategy test, run automatically in the next run, by one module, regime_tester/strategy.py, with a command-line entry. Single-factor spreads are evidence; a strategy is the claim.

Inputs: a signal series or setup rule, a universe, a sizing rule (equal weight, inverse 30-day vol, or event-based unit risk), a rebalance frequency, a holding horizon or exit rule, the costs table, and an optional gate (heat tercile, trend state).
Outputs, by the three fixed periods and by year, net of costs: CAGR, volatility, Sharpe, maximum drawdown, worst 30 days, hit rate, average win and loss, turnover, time in market, capacity (median open interest of names held), and the equity curve. Benchmarks on the same dates: buy and hold BTC, equal-weight universe, and the 200-day rule.
Variants run by default for every admitted signal: long only, long-short, with and without the heat gate, with and without vol targeting. Twelve cells. The verdict names the best cell in validation and reports that same cell in test; the best cell in test is never the one quoted.
Admission to the strategy library: positive net Sharpe in validation and test, maximum drawdown below the benchmark's in both, turnover the costs table can carry, at least 60 independent holding periods. Otherwise it is recorded as "signal admitted, strategy not" with the cell table attached, which is itself a finding.
Live tracking: every admitted strategy is paper-traded from the day of admission in signals/strategies.csv with daily net returns, and its live Sharpe is reported weekly against its test Sharpe.

## 6. Reporting rules
- Verdict first. Every research entry in log.md and in data.json puts the verdict in the first line (admitted at horizon H with gate G, rejected because R, insufficient with n) and the three numbers that decided it in the second. The hypothesis text follows. The dashboard shows the first 400 characters, so the result must be in them.
- Both repositories are pushed at the end of every run, and the commit hash of Hermes-Research is in the STATUS footer. A run that fails to push reports FAIL.
- data.json carries backlog (section 10 of the research program plus the generated items), strategies (the strategy library with its per-period table), and generated (the last ten generated candidates with their scores), on every write.
- The weekly note lists: items run, verdicts, tests since last admission, data items landed, what the generator proposed and why, and the three candidates with the highest score waiting in the queue.

## 7. Queue order from today
1. D1, full perp universe. Nothing cross-sectional has power without it.
2. C2 to C7 in the cycle plan, as parallel subagents once D1 is in, on BTC, ETH and the pooled majors.
3. D2, D4, D6, D7 as separate runs between cycle items.
4. C8 and C9, the scorecards and the risk-off ladder.
5. Cross-sectional items 4 to 8 of the research program on the full universe.
6. First generator pass once the queue is below eight, then continuous.

## 8. Amendments to the cycle plan after C1 and C2

The first two cycle items showed two definitions in RESEARCH_PROGRAM_CYCLE.md to be wrong. These replace them.

Targets are evaluated from candidate days only
- Top candidates: days where the close is within 5 percent of its 60-day high. Top event: the lowest close in the next 30 days is at least 20 percent below today's close. Also report 15 percent within 20 days and 30 percent within 60 days.
- Bottom candidates: days where the close is within 5 percent of its 60-day low. Bottom event: the highest close in the next 30 days is at least 20 percent above today's close and no close in between is more than 7 percent below today's. Also report 30 percent within 60 days.
- Base rates are stated among candidate days, not all days. Episodes collapse consecutive candidate days with the same label. Report episodes per year; a label with more than half its episodes in one year is reported with that caveat attached to every result built on it.
- As a check on the labels, mark swing points with a 20 percent zigzag (the last day before a 20 percent reversal) and report how many zigzag tops and bottoms the event labels catch and miss.
- Rerun C1 on these definitions before any further cycle item, and rerun C2 on the new labels; the ETH funding cell is a live candidate under the amended bar below.

Admission bar for event detectors
- At least 30 episodes in the cell across train and validation combined; lift above 1 in validation with the episode-bootstrap 90 percent interval clear of 1; the train sign agrees.
- The test period is reported in every result and gates admission only once it holds ten or more episodes for that label. Until then an admitted detector is marked "test pending" on the dashboard.
- BTC alone is always reported; it vetoes a pooled result only when BTC alone has fifteen or more episodes in the cell. Pooled results count one episode per overlapping window across names, never one per name.
- The testing budget in section 4 applies to the count of cells tested, not the count of factors.

Queue order, revised
1. D1, the full perp universe, before anything else. Every cross-sectional item depends on it and it is where the program's power is.
2. C1 rerun on the amended targets, then C2 rerun, then C3 to C7 as parallel subagents.
3. D2, D4, D6, D7 between cycle items. Then C8, C9, and the cross-sectional items.

Luke's direct instruction overrides this document. Nothing here relaxes the hard limits.
