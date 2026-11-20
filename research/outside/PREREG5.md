# Pre-registration 5, 2026-11-19: flows and macro (plan item P1/P2 of OBJECTIVE_2026-11-19.md)

Written before any cell is scored. The question: do the inputs that are supposed to move BTC over weeks (flows and
macro) carry stable, out-of-sample information at 10/30/60 days, measured with the same rules as passes 1-3?

## Series (daily, public sources, pulled 2026-11-19)
- stable_supply: USDT + USDC circulating (DefiLlama), 2018+. Reading: 30-day change in percent.
- dxy: FRED DTWEXBGS broad dollar index (published with a few days' lag; used as of its publication date, no lookahead
  correction beyond lag 1, which understates nothing because a later value cannot be known earlier). Reading: 20-day change.
- real10: FRED DFII10 10-year real yield. Reading: 20-day change (percentage points).
- fed_bs: FRED WALCL Fed balance sheet (weekly, forward-filled). Reading: 4-week change in percent.
- spx: FRED SP500 close; ndx: NASDAQCOM. Reading: 20-day return.
- vix: FRED VIXCLS. Reading: level percentile and 5-day change.
- us10y: FRED DGS10. Reading: 20-day change.
- cb_premium: Coinbase BTC-USD close over Binance BTCUSDT close minus 1 (Laevitas spot candles), 2020+. Reading: level
  percentile and 5-day mean.
- etf_flow: spot BTC ETF net daily flow (Farside), 2024-01+. Reading: 10-day sum, percentile of its own history
  (only test and validation periods exist; exploratory).
Non-trading days (weekends for FRED series) are forward-filled onto the crypto calendar; the reading is known at the
prior close (lag 1).

## Hypotheses (sign fixed now), BTC 10/30/60-day forward return and 30-day drawdown
H-stable: stable_supply 30d change top fifth -> positive; bottom fifth -> negative.
H-dxy: dxy 20d change top fifth -> negative; bottom -> positive.
H-real: real10 20d change top fifth -> negative; bottom -> positive.
H-fed: fed_bs 4w change top fifth -> positive; bottom -> negative.
H-spx: spx 20d return top fifth -> positive (risk appetite carries); bottom -> negative. Same for ndx.
H-vix: vix level top fifth -> positive at 30-60 days (fear sells off, then recovers) and negative at 10; vix 5d rise top fifth -> negative at 10.
H-cb: cb_premium top fifth (US demand) -> positive; bottom -> negative.
H-etf: etf_flow 10d sum top fifth -> positive; bottom -> negative (exploratory, 2024+).
Thresholds: fifths of the trailing-365-day percentile (lag 1) as everywhere else. Excess vs all days where the series
exists. Periods train <= 2024-06-30, validation 2024-07..2025-12, test 2026.

## Pass rule
As in OBJECTIVE_2026-11-19.md: same excess sign in all three periods, validation |t| >= 2.5, >= 20 independent episodes
across train + validation at the horizon, and decile calibration (Spearman of score decile vs mean 30d return) >= 0.5
in train and validation for the continuous reading. Anything less is reported as context with its numbers.
Count: 9 series x 2 sides x 3 horizons = 54 return cells + 18 risk cells. About 1-2 chance passes at the 2.5 bar.
Refutation on any pass: lag 2, neighbouring thresholds, drop best 3 validation episodes, and the obvious control
(BTC's own 20-day return, since risk assets move together).

## Addendum, 2026-11-19, written after the macro cells were scored and before these are
H-trend (BTC's own trend, the one input the ensemble test suggested carries calibration): btc 20-day return top fifth
-> positive at 30/60 days (continuation), bottom fifth -> negative; btc 60-day return the same; close above the
200-day mean -> positive, below -> negative; close vs 50-day mean the same. Same pass rule and refutations. These are
not new hypotheses in the literature (time-series momentum) but they have not been scored here as single cells.
