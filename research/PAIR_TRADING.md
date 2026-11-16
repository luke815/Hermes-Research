# Pair trading: calculator inputs, the daily pairs screen, and the backtest

The page now carries a pair calculator that works in the browser from daily closes and 7-day funding: betas to BTC over the window, hedge ratios under four conventions (beta-neutral to BTC, dollar-neutral, vol-neutral, regression of long on short), the residual market beta after the hedge, correlation, the spread's window and 20-day z-scores and half-life, annualized net carry, sized legs for a capital amount, and the dollar risk at a stop set in daily spread-volatility units. It runs today on the twenty names in the daily file. Three things make it a desk tool rather than a toy.

## P1. pair_inputs: the whole universe in the calculator
Written daily by the scheduler after the refresh, from the point-in-time panel and the funding store:
```json
"pair_inputs": {
  "as_of": "2026-11-17", "funding_unit": "pct_8h",
  "dates": ["... last 250 trading days ..."],
  "names": { "SOL": { "close": [250 values], "funding_7d": 0.0061, "oi_usd": 870000000, "vol_30": 58.0, "sector": "L1" }, "BTC": { }, "ETH": { } }
}
```
Every name that clears the liquidity floor, plus BTC and ETH. Closes are the venue with the highest open interest. `funding_7d` in the unit the source reports; `funding_unit` says which (`pct_8h` for percent per 8 hours, `fraction_8h` for a fraction). Done when the calculator's name list on the page shows the universe count.

## P2. The daily pairs screen
A scheduler job over every ordered pair in the liquid universe (sector pairs first, then every name against BTC, ETH and SOL, then cross-sector pairs with correlation above 0.6), on a 90-day window of daily closes, written to `pairs_board`:
- For each pair: hedge ratio (beta-neutral to BTC), correlation, Engle-Granger cointegration p-value on log prices, half-life of the spread, window z and 20-day z, net carry, each name's 30-day vol and open interest.
- Two lists, top 25 each: mean-reversion candidates (cointegration p below 0.05, half-life between 3 and 30 days, absolute window z above 2, liquidity floor on both legs), and relative-strength spreads (30-day return spread in the top or bottom decile with both legs trending the same way against their 50-day, for momentum pairs). Every row carries the direction (which leg long), the hedge ratio and the carry.
- Rows carry `bt_sharpe` once P3 has run for that pair type; `null` before.
```json
"pairs_board": { "as_of": "2026-11-17", "note": "", "rows": [ { "long": "NEAR", "short": "ETH", "type": "reversion", "sector": "L1", "z": -2.3, "z20": -1.8, "half_life": 12, "coint_p": 0.02, "corr": 0.61, "hedge": 1.2, "carry": 2.1, "oi_long": 120000000, "oi_short": 5400000000, "bt_sharpe": null } ] }
```
The screen is a filter, not a signal; the page labels it so.

## P3. The pair-rule backtest
Through strategy.py, on the point-in-time universe, three fixed periods, per year, net of costs on both legs and funding carry:
- Reversion rule: enter when the window z crosses beyond 2 (long the cheap leg, short the rich leg, beta-neutral), exit at z crossing 0, stop at 2.5 daily spread vols against, maximum hold 30 days, only pairs cointegrated on the trailing window at entry (p below 0.05, half-life 3 to 30). Variants: z thresholds 1.5 and 2.5, dollar-neutral instead of beta-neutral, no cointegration filter, sector-only pairs.
- Relative-strength rule: enter the top-decile 30-day spread in the direction of the spread, beta-neutral, hold 10 days or exit on a 20-day spread reversal, stop at 2.5 daily spread vols. Variants: 14-day window, vol-neutral.
- Metrics: pair-level hit rate, mean net return per pair trade, Sharpe of the pair book, maximum drawdown, average hold, stop-out share, carry contribution, turnover, capacity (median open interest of the smaller leg). Admission as in SWEEP_V2 section 3; a rule that passes writes `bt_sharpe` into the board for its pair type and feeds the ideas list and the book's pairing step.
- Until admitted, the board rows read "backtest pending" and the page says so.

## P4. Calculator inputs for intraday
Once the 4-hour stores exist, `pair_inputs` gains `close_4h` (last 120 bars) so the calculator can be switched to a 4-hour window for entry timing. Not before.

## Queue
P1 and P2 after L4 (they need the universe panel); P3 after L6 (it needs strategy.py's costs and the three-period plumbing on the new panel). P1 is one run, P2 one run, P3 two runs.
