# Laevitas v1 inventory

Source: https://api.laevitas.ch, fetched 2026-11-16 with the apikey header from .env. The v2 host at apiv2.laevitas.ch returns 403 from this machine, so v1 is the source until that changes. Catalogue saved at data/laevitas/catalog_v1.json (164 endpoints, 81 historical). Instrument list saved at data/laevitas/instruments.json, parsed from the `data` array of /analytics/futures/instruments (the wrapper holds a date and the rows; an earlier save dropped rows and is kept as instruments.json.bak_4016).

## Exchange instrument counts

From /analytics/futures/instruments on 2026-11-16, 5,885 instruments. The response timestamp was 1794841380.

Perpetuals, 5,185 across all 13 exchanges named by /exchanges:

- BITGET 935
- BYBIT 914
- BINANCE 824
- OKX 809
- HUOBI 425
- HYPERLIQUID 350
- DYDX 296
- KRAKEN 209
- DERIBIT 153
- PARADEX 84
- BITFINEX 76
- NADO 73
- BULLISH 37

Dated futures, 171: DERIBIT 67, BYBIT 44, OKX 28, BINANCE 14, KRAKEN 10, HUOBI 8. /exchanges also names futures on these six and no others.

Options, 529, from the same response: paradex 131, bybit 112, derive 72, gate 70, deribit 52, binance 38, okx 38, bullish 16. /exchanges names the same eight option venues. /analytics/options/Instruments returned HTTP 500, so the options count comes from the futures instrument endpoint.

## First date per family

Probed on BTC, one month at a time, then the first non-empty month pulled in full. The date is the earliest `date` field in that month, converted from milliseconds.

- Perpetuals, /historical/derivs/perpetuals/BINANCE/BTCUSDT: 2021-03-26. Fields on that bar: price, index, basis, funding, yield, volume, volume_coin.
- Dated futures, /historical/derivs/futures/BINANCE/BTCUSDT_240628: 2023-12-30. This is one contract's first bar, not the family's; the contract expiry is in the symbol.
- Futures annualized basis, /historical/futures/futures_annualized_basis/BTC/30: 2021-03-30.
- Liquidations, /historical/derivs/liquidation_by_currency/binance/BTC: 2021-11-20.
- Options DVOL, /historical/options/dvol/deribit/BTC: 2021-03-25.
- Options ATM IV, /historical/options/atm_iv/deribit/BTC: 2019-03-31.
- Options skew 25-delta, /historical/options/type/skew/deribit/BTC/25d: 2019-03-31. The type token is `25d`; `25delta` returns HTTP 400.
- Options risk reversal 25-delta: 2019-03-31.
- Options butterfly 25-delta: 2019-03-31.
- Options implied minus realized, /historical/options/iv_rv/deribit/BTC: 2019-03-30.
- Options open interest total, put-call open-interest ratio, put-call volume ratio, gamma exposure index and max pain, all deribit/BTC: 2020-09-25.
- Spot, /historical/spot/binance/BTCUSDT/1d: 2018-02-01.

## First date per perpetual exchange

BTC perpetual on each venue, same probe. The five venues absent from the earlier instrument file return history when asked by symbol.

- BINANCE BTCUSDT: 2021-03-26
- HUOBI BTC-USDT: 2021-07-02
- BITFINEX tBTCF0:USTF0: 2021-07-13
- DYDX BTC-USD: 2021-08-31
- BITGET BTCUSDT: 2023-02-16
- PARADEX BTC-USD-PERP: 2024-05-10

BYBIT, OKX, HYPERLIQUID, KRAKEN, DERIBIT, NADO and BULLISH are in the instrument list and were not re-probed for a first bar this run. Their per-venue first date is not pinned.

## Delisted names

The history endpoint returns them by symbol. Probed on Binance for April 2022: LUNAUSDT 31 rows, FTTUSDT 16 rows, SRMUSDT 31 rows.

## What this does not cover

The remaining 81 historical endpoints were not each probed for a first bar. The families above are the ones the catalogue groups history under. A per-endpoint first date is L2's inventory, written as the puller stores each series.
