# Q5 pre-registration

Committed before any cell is scored.

Hypothesis: crowded shorts, read from funding, precede a positive return. The
outside pass found the sign but not the drift control, so the question is
whether the excess over the same-period mean survives once BTC's own return
is subtracted for the alts.

Members, each scored separately and reported in one table:

- btc_binance: the Binance BTC funding rate, trailing 365-day percentile at
  or below 0.1.
- btc_oiw: the open-interest-weighted funding across venues for BTC, trailing
  365-day percentile at or below 0.1.
- btc_z30: the Binance BTC funding rate, 30-day trailing z-score at or below -2.
- eth_binance: the same percentile rule on the Binance ETH funding rate.
- alts: the same percentile rule on each alt's own funding rate, pooled.

The rank and the z-score use the preceding window only, minimum 252 bars for
the rank and 30 for the z-score, and the flag is lagged one bar. A name is in
the alt pool on a date only when it has a funding value that date.

Horizons: the forward return at 3 and 5 days. The excess is the mean forward
return on flagged days minus the mean on every day of the same period where
the signal is defined. For the alts, a second column subtracts BTC's own
forward return on the same days. Episodes are runs of consecutive flagged
days, and for the pool a run is a date with at least one flagged name.

Periods, fixed and never moved: train through 2024-06-30, validation
2024-07-01 through 2025-12-31, test from 2026-01-01.

Pass: the excess keeps its sign in validation and in test, the episode count
across train and validation is at least 20, and the same sign holds on BTC,
ETH and the alt pool. For the alts the BTC-subtracted excess is the one that
decides. A sign flip is rejected. Below the count is insufficient.
