# Research backlog

Ordered by expected information gain. Work the top item when idle. A candidate moves to the log once tested, whether admitted or rejected.

## Next ten

1. Cross-venue funding divergence. Binance versus Bybit versus OKX funding on the same names. A venue paying far more than the others is leverage concentrated in one place. Coinalyze carries per-exchange funding; not yet pulled.
2. Cross-venue basis divergence. Same idea for the 90-day annualized basis. Laevitas `futures_annualized_basis` returns a per-market map; we currently average it.
3. Hyperliquid versus CEX positioning. Hyperliquid funding and OI against the Binance aggregate. Laevitas perpetuals catalog includes Hyperliquid (342 instruments).
4. Per-asset OI concentration. Herfindahl of open interest across the 20-name basket. We have the OI history; the concentration series has not been built.
5. Stablecoin supply change. USDT and USDC aggregate supply, daily, as a liquidity proxy. Free from DeFiLlama or CoinGecko. Not yet pulled.
6. DEX versus CEX volume share. DeFiLlama DEX volume against CEX volume. A rising DEX share has preceded speculative phases.
7. Order-book imbalance from L2 snapshots. Laevitas retains L2 books for a rolling window. Bid-side dominance at the top of book as a short-horizon factor.
8. Realized-versus-implied term structure. The slope of realized vol across lookbacks (7 versus 90) against the implied slope. We have both series.
9. Funding acceleration. The change in the funding z-score, not the level. Level was rejected; the second derivative was not tested.
10. Alt-basket dispersion at 30 and 90 days. The admitted factor is 14-day. Longer windows may carry the swing horizon better.

## Blocked on a source

- Market-wide OI dominance and the put/call ratio. Both need `get_market_positioning_history`, which returns a bare server error. Retry weekly, not more.
- Gamma exposure. History exists but methodology changed on 2026-06-01 and values were reset in October 2025. Unusable until a clean stretch accumulates.
- Raw Twitter sentiment. X search requires a logged-in developer account and the API does not serve multi-year history. Fear & Greed, which includes social volume, was tested and rejected as redundant with momentum.

## Rejected (do not retest without a new transform or horizon)

Raw funding level, OI spread, BTC dominance, liquidations, long/short ratios, breadth, speculation, volume participation, OI momentum, skew, risk reversal, vol premium, DVOL, options term structure, basket funding z-score, Fear & Greed. Each failed sign stability, redundancy, or the incremental-information test. Details in log.md.
