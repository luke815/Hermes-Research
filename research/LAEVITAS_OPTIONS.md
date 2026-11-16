# Laevitas options and derivatives: use all of it

Laevitas is the primary derivatives source from now on. This document lists the datasets it serves, turns each into measures the sweep can test, and says where every series goes: the sweep (single-asset cells on BTC and ETH, cross-sectional cells where an alt has listed options, and conditioning variables for every alt signal), the derivatives panel on the page, the risk dial's inputs, and the cycle scorecard's families. The discipline does not change: every measure passes the lookahead test, carries metadata, enters the budget, and is admitted only under SWEEP_V2 section 3.

## 1. First run: the inventory, from the API, not from memory
Before any measure is written, one run enumerates what the subscription actually serves and saves it to data/laevitas_catalog.json: every endpoint reachable with the key in .env over REST (and the MCP as fallback), per endpoint the assets, exchanges, tenors or strikes it takes, the earliest date returned, the finest granularity (daily, hourly, 5-minute), the largest window one call accepts, and the rate limit. Ten calls per endpoint is enough. The catalogue is the ground truth for everything below; a dataset listed here that the catalogue does not hold is logged as absent, not approximated.

## 2. The catalogue as measures
Per asset (BTC, ETH; and SOL, XRP, BNB or any alt with listed options on Deribit, OKX or Bybit), daily unless marked, with the transforms of RESEARCH_LOOP section 3 (level percentile, z-score, change, persistence, acceleration, divergence from price, cross-sectional rank where more than one asset has the series).

Implied volatility
- ATM implied vol by tenor: 1, 7, 14, 30, 60, 90, 180 days. Term slope (90 minus 7, 30 minus 7), term curvature, inversion flag (front above back) and days inverted.
- Volatility index (DVOL or equivalent) level, 1-day and 7-day change, 1-year percentile; hourly where served, for the intraday layer.
- Implied minus realized at 7 and 30 days (the variance risk premium); implied minus the realized that followed (ex post, as a label only, never a feature).
- Forward implied vol between tenors; vol of vol of the index over 30 days.
- IV rank and percentile as the vendor computes them, kept beside the house percentile for cross-check.

Skew and smile
- 25-delta and 10-delta risk reversals by tenor; 25-delta and 10-delta butterflies by tenor; put-minus-call IV at fixed deltas.
- Skew term slope (90-day skew minus 7-day); skew change over 1, 5 and 20 days; skew percentile against its own year; sign flips of the risk reversal and days since the flip.
- Full surface snapshots where served (IV by delta and tenor), stored daily for later surface-shape measures.

Open interest and expiries
- Total options open interest in contracts and notional, by exchange and summed; 1-day, 7-day and 30-day change; percentile.
- Call and put open interest separately; put-call open interest ratio and its percentile; the same by tenor bucket (front month, next, back).
- Open interest by strike: max pain for the nearest expiries; distance of spot from max pain; the strikes holding the largest call and put open interest and their distance from spot (the "walls").
- Open interest by expiry: notional expiring in the next 7 and 30 days as a share of total; the largest expiry ahead and days to it.

Volume and flow
- Options volume by day, notional and premium; by exchange; put-call volume ratio and its percentile.
- Taker-side flow where served: calls bought minus sold, puts bought minus sold, net premium paid; block trade volume and share; large-trade counts.
- Volume by tenor and by moneyness (OTM calls, OTM puts) as shares of total; a "call chasing" flag (OTM call volume share in its top decile) and a "put hedging" flag (OTM put volume share in its top decile).

Dealer positioning and greeks
- Aggregate gamma exposure by strike and total; the gamma flip level and spot's distance from it; net dealer delta; vanna and charm where served.
- Changes in total gamma over 1 and 5 days; gamma concentration (share of gamma within 5 percent of spot).

Futures and perpetuals, per instrument and per exchange
- Basis by tenor (1 week, 1 month, 3 months) annualized; the basis curve slope; perp premium against the index; basis percentile.
- Funding per instrument and per exchange; OI-weighted and simple averages; cross-venue dispersion; Hyperliquid minus CEX funding per name.
- Open interest per instrument and per exchange, notional and contracts; venue concentration; OI against the instrument's 90-day high; OI change on down days minus up days.
- Liquidations per exchange and per instrument, long and short, as a share of open interest; cascade flags.
- Long-short account and position ratios where served; top-trader positioning where served.

Realized and cross-measures
- Realized vol 1, 7, 30 days from the vendor and from the house price series (cross-check); vol ratio 7 to 30; vol of vol.
- Implied minus realized by tenor; skew minus realized skew of returns; put-call ratio minus its 30-day mean.

Every measure carries family (options_iv, options_skew, options_oi, options_flow, options_greeks, derivatives, realized), the inputs, minimum history, type (level, oscillator, flag, count) and the asset coverage the catalogue reports. The count of distinct measure, target and universe combinations per family goes into the deflated bar.

## 3. Pull plan
- REST with the key in .env, batched where the API allows, through the shared rate bucket with its own reserved allowance; the MCP only where REST lacks an endpoint. One resumable puller daemon for the whole catalogue, registered through procmgr, writing one store per endpoint under data/laevitas/ with first and last dates in INVENTORY.md.
- History first for BTC and ETH (every series, full depth), then alts with options, then per-instrument perps for the universe. Daily series first; hourly DVOL, skew and funding after, for the intraday layer.
- Daily append in the scheduler after the refresh; failures posted as a FAIL with the endpoint and the HTTP status, never a silent gap, and never a filled value.
- Cross-checks written once: Laevitas aggregate funding against Coinalyze on the 20 names; vendor realized vol against the house series; vendor IV percentile against the house percentile. Largest mismatch reported with the series kept as primary.

## 4. Where each series goes
- The sweep: single-asset cells on BTC and ETH against forward returns at 1, 3, 10 and 30 days and the amended top and bottom events; ETH/BTC relative targets; pooled BTC and ETH where the series exists for both. Cross-sectional cells for the perp series across the universe and for the options series across every asset that has them. Options and skew measures also enter as conditioning variables on every cross-sectional alt cell (does a reversal work when the market is put-rich or call-chasing), which is where market-level options data can price alt behaviour.
- The derivatives panel on the page: every market-level series with value, change, percentile, 30-day sparkline and a one-line read, grouped by the families above, BTC and ETH side by side, alts with options as additional tabs.
- The risk dial: implied minus realized, skew percentile, term inversion, put-call open interest percentile, gamma flip distance and total options open interest change join the inputs in RISK_REGIME section 1, each with a stated direction, and are tested like every other input.
- The cycle scorecard: the options families are C5 reopened, with the full catalogue rather than six series: skew tails, IV percentile extremes, put-call extremes, term inversion and call-chasing flags, tested as candidate-day event detectors on BTC and ETH, pooled.
- The intraday layer: hourly DVOL, skew and funding feed the 4-hour setups and the live board's crowding reads.

## 5. Power, stated plainly
Options history on BTC and ETH runs from 2019 to 2021 depending on the series, so single-asset tests at 10 and 30 days remain thin (20 to 40 independent observations). The signals with enough sample are the 1 to 3 day horizons, the candidate-day events on the pooled pair, and the conditioning of cross-sectional alt cells by market-level options state, which multiplies the options series by hundreds of names per day. Report every result with its independent n; a thin one is "insufficient", never a pass or a fail.

## 6. Queue
- L1. The catalogue run (section 1). One run.
- L2. The puller daemon over the catalogue, BTC and ETH history first; INVENTORY.md. Two runs, then continuous.
- L3. Measures and metadata for every series in the catalogue, with lookahead tests; re-enumerate. One run.
- L4. Derivatives panel on the page from the full catalogue. One run.
- L5. Options inputs into the risk dial and C5 reopened on the catalogue. Two runs.
- L6. Options state as conditioning on the cross-sectional cells in the sweep. One run.
L1 to L3 run ahead of everything in the current queue except the sweep work-list fix, because every later research item wants these series on disk.
