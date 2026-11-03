# Data: the point-in-time universe and the full source map

## 1. D1, done properly: the historical symbol list
Coinalyze's market list is today's listings. The names that were delisted are still served by symbol, so the missing piece is only the list. Build it from sources that are themselves historical.

Step 1. Binance historical symbol set. The public archive at data.binance.vision lists every USDT-margined perp that ever traded under `data/futures/um/daily/klines/` (and monthly). Read the bucket listing (an S3 XML listing, paginated with a marker; follow it to the end) and keep every symbol folder. LUNAUSDT, FTTUSDT, SRMUSDT and the other delisted perps are there with their full kline history. Save the list with each symbol's first and last file date; the last date is the delisting date.

Step 2. Bybit historical symbol set. The public archive at public.bybit.com/trading/ lists symbols the same way. Keep the folder names with first and last dates.

Step 3. OKX. No archive of the same kind. Take the union of (a) OKX symbols in Coinalyze's current list, (b) every ticker from steps 1 and 2 rendered as the OKX symbol, requested from Coinalyze by symbol, keeping the ones that return history.

Step 4. Candidate tickers beyond the archives. Union the base tickers across all 5,541 markets Coinalyze lists on every exchange (a name Binance delisted often still trades on Gate, MEXC or Bitget) and the full CoinGecko coin list (free endpoint, all symbols). Request each as a Binance, Bybit and OKX perp from Coinalyze in batches of 20 symbols per call with a one-week range; anything that returns bars and is not in today's list is a delisted name. This is a one-off sweep of a few thousand calls; run it in the background with resume.

Step 5. The universe table. One row per (exchange, symbol): first bar, last bar, delisted flag, delisting date. Membership on date t: the name has a bar on t-1 and meets the liquidity rule. Save as data/universe.csv with a hash in the inventory. Every cross-sectional result cites the universe hash it ran on.

Step 6. Quantify the bias once. For each date, the share of the top 100 by open interest that is delisted today, by year. That number goes next to every survivor-labelled result produced before this landed, and the label comes off results run on the new table.

Step 7. Pull the delisted names' full series from Coinalyze by symbol into the same panel format, and cross-check a sample of 20 names against the Binance archive klines and funding. Report mismatches above 0.5 percent in close or any gap of more than one day.

## 2. Source map
What exists, what it covers, what it costs, and what it is for. Every source is pulled by a script with a first-date inventory and a verify_panel pass; every new series is named by the dashboard spec rule and visible on the page the day it lands.

Derivatives, in use
- Coinalyze (key in .env): daily and intraday OHLCV, funding, open interest, liquidations, long/short, per market, Binance, Bybit, OKX and others, 2020 onward for the oldest names. The backbone for the cross-section.
- Laevitas (MCP): options (DVOL, ATM IV, skew, risk reversal, term structure where the endpoint works), basis, OI-weighted cross-venue funding, realized vol, per-instrument perps including Hyperliquid (342 instruments from December 2024). The backbone for positioning and the options family.

Derivatives, free, not yet used
- Binance public archive (data.binance.vision): klines, funding rates, open interest and long/short metrics, taker buy/sell volume, per symbol including delisted, no key. Second source for the Binance leg of the universe and the only source for delisted names' intraday bars.
- Bybit public archive (public.bybit.com): trades and klines per symbol including delisted.
- Hyperliquid API (api.hyperliquid.xyz, info endpoint): funding history, candles, open interest, per perp, from listing, no key. Independent of Laevitas for the Hyperliquid leg.
- Deribit API: historical index and volatility index, and settlement data, no key for public endpoints. Cross-check for DVOL.

Spot and market structure, free
- Binance and Bybit spot archives: spot klines and taker buy/sell, for spot-versus-perp volume share and spot-led versus leverage-led moves.
- CoinGecko API (free tier, rate limited): market cap, volume and supply history per coin, the coin list, categories and sector tags. Sector tags are what a sector breadth factor needs.
- CryptoCompare (free tier): hourly OHLCV across venues and a social data series.

Flows, on-chain, sentiment, free
- DefiLlama API: stablecoin supply by asset and chain, DEX volumes, fees, TVL by chain and protocol, no key. Liquidity and participation factors.
- Coin Metrics community API: daily reference rates, market cap, realized cap, MVRV, active addresses, transfer value, for BTC, ETH and a few hundred assets, no key. The on-chain family.
- Farside Investors: daily spot BTC and ETH ETF flows by issuer, scraped from the public tables, from January 2024.
- Alternative.me: Fear and Greed daily, in use.
- mempool.space and blockchain.com: hash rate, fees, mempool size, for BTC miner and congestion factors.
- Santiment and Glassnode free tiers: a handful of metrics each with delays; use only where the series is daily and complete.

Macro, free
- FRED (free key): DXY proxies, US 2-year and 10-year yields, breakevens, Fed balance sheet, M2. stooq.com: daily index and FX closes without a key (NDX, SPX, DXY, gold).

Events and supply
- Token unlock schedules: no free complete source; TokenUnlocks and CryptoRank publish schedules behind paywalls, DefiLlama has an emissions endpoint for a subset. Use DefiLlama's where present and log the gap.
- Exchange listing and delisting dates: from the archives in section 1 and Binance's announcement pages.

Paid, if ever justified
- Glassnode or CryptoQuant for exchange netflows and cohort on-chain data; Kaiko or Amberdata for order books and trades across venues; Velo for cross-venue derivatives in one feed. Not before the free sources are exhausted and a tested factor family is blocked on data only they have.

## 3. What exhaustive means here
Exhaustive is not every series. It is: every family in the search space has at least one complete, point-in-time, two-source-checked series behind it; the universe includes the names that died; every series has a first-date inventory and a freshness check; and a factor that is rejected is rejected on the data, not on a gap. The sections above get the program there. Beyond that, more data adds candidates to the generator but does not change the bar.
