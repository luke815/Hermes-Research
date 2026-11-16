# Laevitas v1 inventory

Source: data/laevitas/catalog_v1.json, fetched 2026-11-16 from https://api.laevitas.ch/api/catalog/v2 with the apikey header. The v2 host at apiv2.laevitas.ch returns 403 from this machine, so v1 is the source until that changes.

## Counts
- 164 endpoints in the catalogue, 81 of them historical.
- Historical by family: options 45, futures 24, derivs 9, spot 2.
- Exchanges: the /exchanges endpoint returns the list grouped by instrument type. Not counted here because the probe was not run this turn.

## Earliest date, probed on BTC
Each probe asked for 2019 and 2021 and got nothing, then 2021-10 and got rows. So the history starts in or before October 2021, not in 2019. The exact first bar per series is not pinned to a day yet.

- Perpetuals, /historical/derivs/perpetuals/binance/BTCUSDT: rows from 2021-10, daily. Fields confirmed on 2022-06-15: price, index, basis, funding, yield, volume, open_interest, oi_volume24h, long_short_ratio, next_funding.
- Dated futures basis, /historical/futures/futures_annualized_basis/BTC/30: rows from 2022-01, daily.
- Liquidations, /historical/derivs/liquidation_by_currency/binance/BTC: 49 rows in January 2022, daily.

## Not probed
The 45 options history endpoints and the remaining futures endpoints were not probed this turn. Their earliest dates are unknown until each gets one call, which is the rest of the inventory.

## Delisted names
The history endpoint returns them by symbol. Probed on Binance for April 2022: LUNAUSDT 31 rows, FTTUSDT 16 rows, SRMUSDT 31 rows. Delisted names are in the history, not only the live list.

## Instrument list, 2026-11-16
From /analytics/futures/instruments: 4,016 instruments. Perpetuals 3,324 across 8 exchanges: BYBIT 880, BINANCE 824, OKX 808, HYPERLIQUID 350, KRAKEN 209, DERIBIT 154, NADO 73, BULLISH 26. Options 529, dated futures 163. Saved at data/laevitas/instruments.json.

Five perpetual exchanges from /exchanges are absent from this list: BITFINEX, BITGET, DYDX, HUOBI, PARADEX. Their instrument counts are unknown until a list endpoint returns them. L1 is not done.
