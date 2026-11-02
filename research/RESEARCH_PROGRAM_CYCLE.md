# Research program addendum: tops, bottoms and when to take risk off

This adds a cycle layer to RESEARCH_PROGRAM.md and retires the 10-day return forecast from the top of the dashboard. The question changes from "what is BTC's expected return" to two event questions the data can answer: how likely is a damaging drawdown from here, and how likely is a durable low. The regime score stays as context. The discipline rules, the three fixed periods, the single writer and verify-before-report all apply.

## 1. Targets, defined as events
All targets are computed from the close on day t, looking forward only, and are used as labels, never as features.

- Top event, T(h, x): the lowest close within the next h days is at least x percent below today's close. Primary: h = 30, x = 15. Also report h = 20 with x = 10 and h = 60 with x = 25.
- Bottom event, B(h, x, y): the highest close within the next h days is at least x percent above today's close and no close in between is more than y percent below it. Primary: h = 30, x = 15, y = 7. Also report h = 60, x = 30, y = 10.
- Episode: consecutive days where the label is true, collapsed into one. The number of episodes is the honest n. A detector is evaluated on episodes, never on days.
- Base rates: share of days and of episodes on which each target is true, per period and per year. Every reported probability sits next to its base rate.

Expect roughly 15 to 25 top episodes and a similar number of bottom episodes on BTC since 2020. That is thin. Two things raise the count: pooling across BTC, ETH, SOL and the ten largest alts with every feature normalized per asset (clustering the statistics by date, because assets move together), and running the slow-cycle version on weekly bars where the point is cycle extremes rather than swings. Report BTC alone and the pooled panel side by side.

## 2. Factor families
Each factor is computed per asset, lagged one bar, with a 1-year rolling percentile (past data only) and a stated direction: which extreme argues for a top, which for a bottom. Thresholds start at the 90th and 10th percentiles and must pass the neighbouring-value check (85 and 95, 5 and 15).

Positioning and leverage
- Funding: 7-day average percentile; days in a row above the 80th (top) or below the 20th (bottom) percentile; funding censored at the Binance cap counts as the cap.
- Open interest: OI in USD against its 90-day high; 30-day OI change; OI divided by 30-day average volume (crowding); OI change on down days minus up days over 7 days.
- Liquidations: long liquidations over 3 days as a share of OI (bottom when extreme); short liquidations likewise (top when extreme after a run); days since the last cascade.
- Long/short ratio 30-day z-score.
- Basis and perp premium: 90-day annualized basis percentile (steep contango at tops, backwardation at bottoms); cross-venue dispersion of funding.
- Options, BTC and ETH: DVOL percentile; DVOL minus 30-day realized vol; 25-delta skew and risk reversal percentiles (puts rich at bottoms, calls rich at tops); term structure slope if the endpoint recovers.

Trend exhaustion and extension
- TD Sequential on daily and weekly bars. Setup: nine consecutive closes above the close four bars earlier (sell setup) or below (buy setup). Countdown: thirteen closes at or above the high two bars earlier (sell) or at or below the low two bars earlier (buy), counted after a completed setup, cancelled by a close below the setup's lowest low (sell) or above its highest high (buy). Record completions as events and perfection as a flag; test setups and countdowns separately.
- RSI 14 daily and weekly, level and divergence against price over 20 bars.
- Distance from the 200-day average (Mayer multiple) and from the 50-day in ATR units; slope of the 200-day.
- Weekly 20-period SMA and 21-period EMA band: price above, inside, below, and the number of weeks since a cross.
- Pi cycle: 111-day SMA against two times the 350-day SMA, distance and crossing.
- Parabolic extension: 30-day return percentile; acceleration (14-day momentum minus its value 14 days earlier); consecutive weekly closes up or down.
- Distance from the all-time high and days since; drawdown from the 90-day high.
- Bollinger percent-B on weekly bars; weekly MACD histogram turn after an extreme.

Breadth, across the point-in-time universe
- Share of names above their 50-day and 200-day averages; share at 30-day highs minus share at 30-day lows; breadth thrust (share above 20-day rising from under 20 percent to over 80 percent within 10 days) and washout (under 10 percent).
- Alt basket against BTC over 30 days; BTC dominance 30-day change; ETH/BTC 30-day return.
- Median funding across the universe; share of names with funding above their own 80th percentile (crowding breadth).

Volatility
- Realized vol 30-day percentile; vol compression (Bollinger width below its 15th percentile) ahead of breaks; vol spike then fade (DVOL off its 30-day high by 20 percent while price holds, a bottom pattern).

On-chain, sentiment and flows, where a free source is reachable from the machine
- MVRV and realized price (Coin Metrics community API), distance of price from realized price.
- Stablecoin total supply 30-day change (DefiLlama).
- Spot ETF net flows 5-day and 20-day sums (Farside), from 2024 only.
- Fear and Greed, level and 7-day change.
- Each is tested like any other factor. If a source is unreachable, log it and move on; do not substitute a proxy without saying so.

Macro, optional, weekly
- DXY 30-day change, US 10-year yield 30-day change, BTC 60-day correlation with NDX. Test as conditioning variables only.

## 3. Test standard for event detectors
Section 3 of the research program applies, plus:
- Single-factor event test: for each factor and direction, the share of episodes that followed within h days when the factor was in its extreme, against the base rate, with the number of independent episodes, by period and by year, BTC alone and pooled. Report lift (probability divided by base rate) with a bootstrap 90 percent interval resampled by episode.
- Lead time: days from the first extreme reading to the episode start, median and spread. A top signal that fires 90 days early is a different tool from one that fires 5 days early; record which.
- False alarms: share of extreme readings not followed by an episode within h days, and the average return during those false alarms, because the cost of cutting risk early is the thing being traded off.
- Scorecard: admitted factors are binarized at their thresholds and counted, separately for tops and bottoms. Report P(event | k or more firing) and the independent n for every k, by period. The scorecard is the product; a learned weighting replaces equal counts only if it beats them in validation and test by calibration (Brier score) as well as lift.
- Calibration: a reliability table per period, predicted probability bucket against realized event rate, with n. A detector that says 60 percent and is right 60 percent of the time is useful at any n; one that says 90 percent and is right 50 percent is not, whatever its lift.
- Analogs: for the current reading, the ten most recent dates with the same or higher count, what followed over 30 and 60 days, and the maximum drawdown and run-up along the way. This is shown, not scored.
- Weekly layer: the same procedure on weekly bars with h = 12 and 26 weeks for the cycle extremes, with the sample size stated plainly, since there are only a handful of cycle tops and bottoms.

## 4. The risk-off ladder
"When to take risk off" is a rule, so it is tested as one.
- Exposure rule: BTC exposure equals one minus the top score (scaled 0 to 1 by the count of firing top signals over the admitted total), plus a floor; the bottom score adds exposure back. Variants: step function at k firing signals; hysteresis (cut at k, restore at k minus 2).
- Benchmark: buy and hold BTC, and a 200-day moving-average rule, over the same three periods.
- Metrics, net of costs: CAGR, maximum drawdown, worst 30-day return, time in market, number of switches, per year. The claim is a drawdown reduction with a stated return cost, never "beats buy and hold" unless it does in validation and test separately.
- Report the equity curves and the per-year table on the dashboard; the rule is adopted only if it cuts maximum drawdown in validation and in test with a return cost you would accept, and that decision is Luke's, not the agent's.

## 5. Outputs
data.json gains a `cycle` key; the dashboard's forecast strip and forecast pane are replaced by the two gauges, the checklist and the analogs once the first scorecard is admitted. Until then the keys are written as the work exists and the page shows empty states.

```json
"cycle": {
  "as_of": "2026-11-10",
  "top": { "count": 4, "total": 11, "prob_30d": 0.46, "base_30d": 0.21, "n_episodes": 17, "lead_days_median": 12 },
  "bottom": { "count": 1, "total": 10, "prob_30d": 0.09, "base_30d": 0.18, "n_episodes": 19, "lead_days_median": 6 },
  "signals": [
    { "name": "funding_7d_pct", "side": "top", "firing": true, "value": 0.93, "threshold": 0.9, "lift": 1.9, "n": 14, "lead_days": 9 },
    { "name": "td9_sell_daily", "side": "top", "firing": false, "value": 6, "threshold": 9, "lift": 1.4, "n": 41, "lead_days": 4 }
  ],
  "analogs": [ { "date": "2025-07-14", "count": 5, "fwd_30_ret": -11.2, "fwd_30_max_dd": -16.8, "fwd_60_ret": -7.4 } ],
  "ladder": { "rule": "cut to 0.4 at 5 firing, restore at 3", "exposure_now": 1.0,
              "by_year": [ { "year": "2024", "rule_cagr": 71.0, "hold_cagr": 118.0, "rule_mdd": -18.0, "hold_mdd": -32.0 } ] },
  "series": { "top_count": [], "bottom_count": [], "exposure": [] }
}
```

The signals array is the whole checklist, firing or not, so the dashboard can show what is and is not lit. The series arrays align to series.date.

## 6. Backlog insertion
These go into research/backlog.md after item 3 of the research program (the three-period tester), before the cross-sectional items, because the targets and the episode counter are shared infrastructure. One bounded item per night.

- C1. Targets and episode counter: T and B at all horizons, base rates by year, BTC and pooled. No factors yet. Post the episode counts; they bound everything that follows.
- C2. Positioning family, single-factor event tests, daily. Report the table in section 3.
- C3. TD Sequential, daily and weekly, setups and countdowns, as events. Report lead time and false-alarm rate alongside lift.
- C4. Trend exhaustion family: Mayer multiple, Pi cycle, RSI and divergences, parabolic extension, weekly band.
- C5. Options family: DVOL, skew, risk reversal, IV minus RV.
- C6. Breadth family on the 2022-09 universe.
- C7. On-chain, sentiment and flows: source check first, then tests for whatever is reachable.
- C8. Scorecards for top and bottom from everything admitted; calibration table; analogs; write the cycle key.
- C9. Risk-off ladder backtest and per-year table.
- C10. Weekly cycle layer with its stated sample size.

Then the cross-sectional items resume in their existing order. Items C2 to C7 may run in parallel subagents as long as each writes its own results file and the verdicts are serialized in the log.

## 7. What to expect
Top and bottom detection on one asset over seven years will never produce tight intervals; the output is a calibrated checklist with its n stated, lead times, false-alarm costs and historical analogs, which is what a discretionary risk decision needs. The ladder test tells you what cutting risk on that checklist would have cost and saved, year by year. Anything that claims more than that from this data is overfit, and the per-year tables will show it.
