# Risk regime program: when to degross and when to add gross

Goal: a daily number, the gross dial, between 0 and 130 percent of target gross, with the regime state behind it and the rules that set it, for a long-biased liquid crypto book. It is tested as an exposure strategy, not as a forecast: what gross the dial would have run every day since 2020, what that did to drawdown and return against holding, by year, with every whipsaw counted. "Accurate" here means calibrated and honest, not prophetic. A dial that cut maximum drawdown by a third at a cost of a fifth of the return, in validation and in test separately, is a result; a dial that looks perfect in one period is noise.

## 1. Regime inputs
Daily, from data already on the box, each stored as a value, a 1-year percentile (past data only) and a state flag with the thresholds below. Thresholds are round numbers from practitioner use, not fitted, and each is checked at its neighbours.

Trend (the backbone; the 200-day and the weekly band are the two rules with the longest record in BTC)
- BTC close against its 200-day average: above or below, and the distance in percent.
- Weekly band: BTC against the 20-week SMA and 21-week EMA, above both, inside, below both; weeks since the last cross.
- 50-day against 200-day: cross direction and days since.
- Alt basket (point-in-time, equal weight) against its own 50-day and 200-day.
- ETH/BTC 30-day return sign and the alt basket against BTC over 30 days (whether risk is broadening or narrowing).

Volatility
- BTC 30-day realized vol percentile; vol rising or falling over 10 days; DVOL percentile and DVOL minus realized.
- Vol expansion inside a downtrend (vol percentile above 80 with price below the 200-day) and compression after a decline (vol percentile below 20 with price below the 200-day) as separate flags.

Leverage and positioning
- Cross-venue OI-weighted funding percentile and days above the 80th or below the 20th.
- Total open interest against its 90-day high; 30-day change; OI flush flag (down more than 25 percent over 14 days).
- Liquidation cascades: long liquidations over 3 days above 2 percent of total OI.
- 90-day basis percentile (contango steep at the top, backwardation at the bottom).

Breadth and participation (from internals)
- Share of the universe above its 50-day and 200-day; 30-day highs minus lows; breadth thrust and washout flags as defined in the cycle plan.
- Share of names crowded on funding.

Liquidity and flows (where a source exists; logged as unavailable otherwise)
- Stablecoin supply 30-day change (DefiLlama); spot ETF flows 20-day sum (Farside, from 2024); exchange balances if a free source appears.

Macro, weekly, conditioning only
- DXY 30-day change, US 10-year 30-day change, BTC 60-day correlation with NDX.

Drawdown state
- BTC drawdown from its 90-day high and from its all-time high; days since; the alt basket's drawdown from its 90-day high.
- The portfolio's own drawdown from high-water mark, from the paper book and later from the real book if a series is provided.

The heat score enters as one input, not as the answer.

## 2. Regime states and the dial
A rule-based state machine with hysteresis, because a PM can read it and because hysteresis is what stops whipsaw. States, from most to least exposed:
- Risk-on, trend: BTC above the 200-day and the weekly band, alt breadth above 50 percent on the 50-day, funding below the 90th percentile, vol not expanding. Dial 100 to 130.
- Risk-on, early: price reclaims the weekly band from below, or breadth thrust fires, with vol falling. Dial 70 to 100, rising with confirmation.
- Neutral: mixed trend, or trend up with funding above the 90th percentile or OI at highs (crowded). Dial 60 to 80.
- Risk-off, distribution: price below the weekly band with breadth under 30 percent, or a crowded market that has stopped making highs. Dial 30 to 50.
- Risk-off, trend down: below the 200-day and the weekly band with vol expanding. Dial 10 to 30.
- Defensive, after capitulation: OI flush and cascade flags fired within 10 days, breadth washout, funding below the 20th percentile. Dial 20 to 40 with a bias to add on the first reclaim, because this is where the bottom detector's base rates are highest.
Entry and exit use different thresholds (enter risk-off when breadth falls below 30, leave when it rises above 40; enter risk-on above the band by 2 percent, leave below it by 2 percent), and no state changes more than once in five trading days except on a capitulation or cascade flag.
Within a state the dial is scaled by volatility: dial times the ratio of target vol to 30-day realized vol, capped at 1.3 and floored at 0.5, so the same state carries less gross in a wild market.
Emergency cut: a one-day drop in the alt basket beyond its 1-year 1st percentile, or a cascade flag, cuts the dial by a third at that close regardless of state, restored at the next weekly review if the state has not changed.

## 3. Backtest standard
- The dial is run daily since 2020 on BTC, ETH, the point-in-time alt basket, and a reference blend of 40 percent BTC, 20 percent ETH, 40 percent alt basket, each as exposure times next-day return, net of the costs table on every change in exposure and of funding carry on the perp leg.
- Three fixed periods and per calendar year, as in the research program. Nothing is tuned on validation or test; thresholds are the round numbers above and the neighbour check is reported.
- Variants, each counted in the budget: the full dial; trend only (200-day rule; weekly band rule); vol targeting only; trend plus vol targeting; the full dial without hysteresis; the full dial without the emergency cut; the full dial without positioning inputs; the full dial without breadth.
- Metrics per variant, per period and per year: CAGR, volatility, Sharpe, maximum drawdown, Calmar, worst month, worst 30 days, time at each dial level, number of state changes, whipsaw cost (return given up on state changes reversed within 20 days), turnover, and return captured in the top decile of market months against drawdown avoided in the bottom decile.
- Benchmarks on the same dates: buy and hold of each asset and of the blend; the 200-day rule; a 60/40 constant gross.
- Event view: for every top and bottom episode from the cycle counter, what the dial read 10, 5 and 1 days before, and what it did in the 10 days after. Lead time and false alarms per state, as for the setups.
- Admission: the full dial beats buy and hold on maximum drawdown and Calmar in validation and in test separately, beats the 200-day rule on Calmar in both, and no single input removal changes the sign of the result. The best-looking variant on test is never the one reported; the one chosen on validation is.
- Reported with the result: the per-year table, the state timeline, the whipsaw count, and the sentence that says what it cost in return to buy the drawdown reduction. That trade is Luke's decision.

## 4. Live operation
- The dial is computed daily by a scheduler job after the refresh, written to the risk key and shown on the page with the state, the inputs that set it and the rules that fired. State changes and emergency cuts are posted to the home channel at once, with the inputs that caused them.
- A paper track starts the day the key first exists: the dial times the blend's realized return, with its own equity curve on the page against buy and hold, so the live record accumulates from day one whatever the backtest says.
- Analogs: the ten most recent dates in the same state with the same direction of change, and what the blend did over the next 10 and 30 days.
- Weekly review: state changes in the week, whipsaws, the paper track against the backtest expectation, and any input that has been unavailable.

## 5. Dashboard key
```json
"risk": {
  "as_of": "2026-11-13", "state": "defensive_after_capitulation", "dial": 0.32, "days_in_state": 4, "changed_on": "2026-11-09",
  "inputs": [ { "name": "btc_vs_200d", "value": -14.2, "pct": 0.11, "flag": "below", "effect": "risk_off" },
              { "name": "breadth_above_50d", "value": 0.09, "pct": 0.06, "flag": "washout", "effect": "capitulation" } ],
  "rules_fired": [ "below 200d and weekly band", "breadth washout", "OI flush 14d -31%" ],
  "vol_scalar": 0.78, "emergency_cut": false,
  "transitions": [ { "date": "2026-10-31", "from": "risk_off_trend_down", "to": "defensive_after_capitulation" } ],
  "backtest": { "status": "pending", "by_year": [], "variants": [] },
  "analogs": [ { "date": "2025-04-09", "state": "defensive_after_capitulation", "fwd_10": 8.4, "fwd_30": 21.0 } ],
  "paper": { "since": "2026-11-13", "return": 0.0, "hold_return": 0.0 },
  "series": { "date": [], "dial": [], "state": [] }
}
```
The page will carry a dial gauge, a state timeline shaded over BTC price, the inputs table and the per-year backtest table. Until the backtest is admitted the key carries "status": "pending" and the page says provisional.

## 6. Queue
R1. Inputs module: every input in section 1 computed daily from the panels, with percentiles and flags, written to the panel and to the risk key's inputs array. One run.
R2. State machine and dial with hysteresis and the vol scalar; daily job; first live reading posted with the rules that set it. One run.
R3. Backtest harness for exposure strategies in strategy.py (exposure series times returns, costs on changes, carry), with the benchmarks. One run.
R4. The variants and the per-year tables; event view against the episode counter; admission verdict. Two runs.
R5. Analogs, paper track, transitions and alerts. One run.
R6. Weekly review added to the weekly note.
These follow the bottom scorecard in the queue, because they share the episode counter and the inputs, and the bottom scorecard is the smaller build.
