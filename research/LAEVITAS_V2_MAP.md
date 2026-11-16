# Laevitas API v2: endpoint map and pull plan

Base https://apiv2.laevitas.ch, paths under /api/v1, header X-API-Key from .env (LAEVITAS_API_KEY). Rate limit 240 requests per 60 seconds per key: Laevitas gets its own bucket at 200 a minute, separate from the Coinalyze bucket. Every history endpoint takes start, end, resolution (1m, 5m, 15m, 1h, 4h, 1d), limit up to 1000 and a cursor; metadata endpoints return start_date per instrument, which is the first-bar inventory for free. Exchanges: binance, okx, deribit, bybit, hyperliquid. The old analytics API (api.laevitas.ch, docs.laevitas.ch) is a separate product with precomputed charts; check whether the key works there too, but build on v2, which serves the raw data every analytic can be computed from.

## 1. The point-in-time universe from snapshots
GET /api/v1/perpetuals/snapshot?exchange=X&date=D&resolution=1d returns every perpetual on exchange X that existed on day D, with mark, index, open interest, 24-hour USD volume, bid and ask. The same for /futures/snapshot (dated futures) and /options/snapshot (the whole chain, every strike and expiry, with greeks and IV where served).

Build: one perpetuals snapshot per exchange per day from 2020-01-01 to today, five exchanges, about 12,500 calls, an hour at the Laevitas bucket. Write data/laevitas/perp_snapshots/<exchange>/<date>.parquet and derive from them, with no second source needed:
- The universe table (exchange, instrument, first seen, last seen, delisting date) directly, including every delisted instrument, because it appears in the snapshots of the days it traded. This replaces the span tables and the archive sweeps.
- The daily cross-sectional panel of open interest and volume per instrument, from day one.
- Membership on date t from the snapshot of t-1 and the liquidity rule.
Funding and basis per instrument come from /perpetuals/carry with resolution 1d per instrument (metadata first, then one paginated history pull per instrument; about 3,000 instruments, 1,000 bars a call, so under 10,000 calls). Price per instrument from /perpetuals/ohlcvt at 1d, which also carries buy and sell volume, trade counts, liquidation and block volumes, mark and index. Liquidation events from /perpetuals/liquidations by instrument or by currency.

Coinalyze stays only as the cross-check on the 20 names and as the free fallback. The Binance archive stays as a second price source for the cross-check.

## 2. Endpoint to dataset
Perpetuals (the cross-section and the market-level perp series)
- /perpetuals/catalog, /perpetuals/metadata: instrument list and first bar.
- /perpetuals/ohlcvt: price, volume split buy and sell, trade counts, liquidation volumes, block volumes, mark, index. Daily for the universe; hourly and 4-hour for the top 150 (the D4 intraday stores); 5-minute for the live board's top 100 if the WebSocket is not used.
- /perpetuals/open-interest: OI history per instrument or per currency, any resolution.
- /perpetuals/carry: funding and basis history per instrument (perp premium against index).
- /perpetuals/ticker-history: mark, index, bid, ask, spread, sizes, OI, 24-hour volume in one series per instrument.
- /perpetuals/level1 and /perpetuals/orderbook: bid-ask spread, top-of-book sizes, depth at 10, 20, 50, 100 levels, imbalance and microprice, aggregated to 1h or 1d. New measures: book imbalance, depth-adjusted liquidity, spread percentile. Raw snapshots keep 30 days only; the aggregated endpoint is the history.
- /perpetuals/trades/summary: aggregated by exchange, instrument, direction or strategy over a window, with net OI change and block stats. Net taker flow per instrument per day.
- /perpetuals/liquidations: per-event liquidations with side, size and USD. Cascade flags and per-name liquidation shares.
- /perpetuals/snapshot: section 1.

Futures (dated)
- /futures/carry per instrument gives basis by maturity; combined with /futures/catalog and days_to_expiry this is the basis curve by tenor (1 week, 1 month, 3 months) and its slope, for BTC and ETH on Deribit, Binance, OKX, Bybit.
- /futures/open-interest, /futures/ohlcvt, /futures/trades/summary (grouped by maturity and strategy: calendar spreads, hedge rolls) for term-structure positioning. /futures/liquidations.

Options (BTC, ETH and every currency in /options/catalog: the catalogue shows AVAX_USDC on Deribit, so SOL, XRP, AVAX and others with listed options are in scope)
- /options/snapshot per exchange per day: the full chain. From it, daily: total and per-expiry open interest, call and put OI, put-call OI ratio, OI by strike (max pain, call and put walls), days to largest expiry, and gamma exposure by strike from the snapshot greeks. One call per exchange per day; Deribit, OKX, Bybit, Binance.
- /options/volatility: IV and greeks per instrument; /vol-surface/term-structure: constant-maturity ATM IV by tenor (the term slope, inversion, forward vol); /vol-surface/slices: per-expiry smiles for skew and butterflies at fixed deltas; /vol-surface/strikes: per-strike diagnostics; /vol-surface/snapshots for the stored surfaces; /vol-surface/risk for scenario repricing of a position.
- /options/flow/summary: buy and sell pressure, active strikes. The taker-flow measures, call-chasing and put-hedging flags.
- /options/trades/summary grouped by strike, maturity, option_type, direction or strategy, with premium, notional, net OI change, net delta, gamma and vega, block counts. Dealer-positioning proxies and block flow by day.
- /options/open-interest, /options/volume: aggregates per instrument or currency by resolution.
- /options/ohlcvt and /options/ticker-history: per-instrument prices, for the realized-versus-implied cross-checks and for any single-instrument study.

Hyperliquid HyperCore (unique to this source)
- Wallet-attributed fills, liquidation fills, wallet positions and flow rollups, funding payments, TWAP events, resting L4 orders and the L2 book. New families: whale flow (large-wallet net positioning per name), liquidation fills by role, TWAP execution pressure. Enter the sweep as cross-sectional measures for Hyperliquid-listed names once the perp panel exists.

Predictions (Polymarket, HIP-4)
- OHLCVT, tickers and trades for prediction markets. A macro and event conditioning source (rate decisions, election and regulatory markets), not a trading universe. Later.

WebSocket
- trades, OHLC ticker and OHLC VT channels per instrument at 1m to 1d. Candidate replacement for the live board's polling once the REST layer is stable; not before.

## 3. Pull order and budgets at 200 calls a minute
1. Perpetual snapshots, five exchanges, 2020 to today: about 12,500 calls, one hour. Universe, OI and volume cross-section derived the same run.
2. Perpetual carry and ohlcvt at 1d per instrument, metadata first: under 20,000 calls, two hours. Funding, basis and price per instrument, delisted included.
3. Options snapshots, four exchanges, from each exchange's first options date: about 8,000 calls, one hour, larger payloads. Derived daily: OI by type, expiry and strike, put-call, max pain, walls, gamma exposure.
4. Vol-surface term structure and slices for every currency with options, daily history: a few hundred calls. ATM IV by tenor, skew and butterflies at fixed deltas.
5. Options flow summary and trades summary by day for BTC and ETH, then other currencies: a few thousand calls.
6. Futures carry per maturity for the basis curve; perpetual and futures liquidations by currency.
7. Order book aggregates at 1h for the top 150 perps, 30 days back and forward daily; Hyperliquid HyperCore; predictions last.
Everything through one resumable puller daemon under procmgr, one store per endpoint under data/laevitas/, a first-and-last-date inventory in INVENTORY.md, a FAIL posted on any endpoint that errors twice. Daily appends in the scheduler after 05:30 UTC.

## 4. What changes elsewhere
- The universe table, panel_xs and the 150-name book universe are rebuilt from the snapshots; the Binance archive, the Bybit raw-trade slices and the Coinalyze universe pull are retired to cross-check duty. The survivor label comes off every cross-sectional result rerun on the snapshot universe.
- The 20-symbol-batch Coinalyze pulls, the D2 funding slices and the open-interest gap close in one step; the positioning cross-section (funding, OI, OI change, OI against highs, liquidations per name) becomes scoreable across the full universe with history to 2020.
- The options family in LAEVITAS_OPTIONS.md section 2 maps to the endpoints above; every measure there is computable from snapshots, vol-surface and flow. C5 reopens on the full set.
- The derivatives panel on the page reads the same stores. The live board can move to the WebSocket later.
- Cross-checks written once and kept: Laevitas perp OI and funding against Coinalyze on the 20 names; Laevitas price against the Binance archive on 20 names; term-structure ATM IV against the DVOL series already on disk.
