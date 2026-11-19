# Pre-registration, 2026-11-18, written before any cell was scored

Data: the public dashboard file (daily, 2020-01-21 to 2026-11-17). Harness: harness.py, rules fixed there.
Periods: train to 2024-06-30, validation 2024-07-01 to 2025-12-31, test from 2026-01-01.
Horizons: 1, 3, 5, 10 days for BTC/ETH events; 1, 3, 5 for the alt cross-section.
Thresholds: trailing-365-day percentile >= 0.9 ("top") or <= 0.1 ("bottom"); z-score >= 2 / <= -2 where stated.
Pass rule: same sign of the spread in all three periods; validation |t_nw| >= 2; test spread same sign; at least 30
independent episodes across train and validation; validation net > 0 after costs and carry. Anything else is
insufficient or rejected. A PASS here is a candidate for Hermes to confirm on the full universe, not a signal.

Nothing outside this list is scored. If an agent scores something else, it is labelled exploratory and does not count.
Total pre-registered cells: 9 families, 46 event cells x 4 horizons + 6 cross-section cells x 3 horizons = 202 cells.
With 202 cells, about 10 would pass a |t|>=2 validation bar by chance alone. A family is interesting only if several
related cells pass together and the sign matches the hypothesis.

## F1. Options: skew and risk reversal (BTC and ETH)
Hypothesis: when puts are unusually bid (skew high / risk reversal very negative), fear is priced and near-term returns are positive; when calls are bid, negative.
- skew_btc pct365 top -> expect positive forward BTC return; skew_btc pct365 bottom -> negative
- rr_btc pct365 bottom -> positive; rr_btc pct365 top -> negative
- skew_eth pct365 top / bottom; rr_eth pct365 bottom / top (ETH returns)
- skew_btc chg7 z90 top (skew rising fast) -> positive

## F2. Options: implied minus realized vol, DVOL level
Hypothesis: a large implied-realized premium (fear) precedes positive returns; DVOL at a one-year high marks capitulation.
- vrp_btc = dvol_btc - rv_btc, pct365 top -> positive; bottom -> negative
- dvol_btc pct365 top -> positive (contrarian); dvol_btc pct365 bottom (complacency) -> negative
- vrp_eth, dvol_eth same

## F3. Funding extremes (reversal)
Hypothesis: crowded longs (funding top decile) precede negative returns; crowded shorts precede positive.
- btc_funding pct365 top -> negative; bottom -> positive
- eth_funding pct365 top / bottom
- oiw_funding_btc pct365 top / bottom (cross-venue, OI-weighted)
- alt_funding pct365 top / bottom (on alt_price, the 20-name basket)
- btc_funding z30 >= 2 -> negative; <= -2 -> positive

## F4. Liquidations (cascade reversal)
Hypothesis: a day of extreme liquidations marks forced selling and precedes a bounce (1-5 days).
- liq_BTC pct365 top -> positive; liq_ETH pct365 top -> positive
- liq_BTC pchg7 z90 top (liquidations surging) -> positive
Note: the long/short split is not in the file, so direction is inferred from the price move; this is a weaker test.

## F5. Open interest
Hypothesis: open interest at a one-year high with price up is crowding (negative); a sharp OI drop is a flush (positive).
- oi_BTC pct365 top -> negative; oi_BTC pchg7 z90 bottom (flush) -> positive
- oi_ETH same
- btc_oi_share pct365 top (capital rotating to BTC) -> alts underperform: tested as alt_price event, negative

## F6. Basis and term structure
Hypothesis: basis at a one-year high is leveraged-long crowding (negative over 5-10 days); very low or negative basis is washed-out (positive).
- basis_btc pct365 top -> negative; bottom -> positive
- basis_eth same
- basis_btc chg7 z90 bottom (basis collapsing) -> positive

## F7. Long/short ratio
Hypothesis: retail long/short ratio at an extreme is contrarian.
- lsr_BTC pct365 top -> negative; bottom -> positive
- lsr_ETH same

## F8. Breadth and dispersion
Hypothesis: when few alts hold their trend (dispersion high) risk is off and BTC underperforms over 5-10 days; dispersion low precedes alt rallies.
- dispersion_14 pct365 top -> BTC negative; bottom -> alt_price positive

## F9. Alt cross-section (18 coins, long top 4 short bottom 4)
Hypothesis: short-term reversal (last 1-3 day losers outperform), funding extremes reverse, OI builds are crowding.
- xs_rev1: signal = -(1-day return); xs_rev3: -(3-day return) -> expect positive spread (reversal)
- xs_mom14: 14-day return -> momentum, sign unknown; reported as is
- xs_fund: -(funding pct365) -> crowded longs underperform -> positive spread
- xs_oi7: -(OI 7-day % change) -> OI builds underperform -> positive spread
- xs_liq: liquidations pct365 -> bounce -> positive spread

## Robustness, applied to anything that passes
1. lag=1 (take the position a day later): must keep sign and most of the spread.
2. Threshold neighbours 0.85/0.95 (or 0.05/0.15): must keep sign.
3. Exclude 2020-2021 from train: must keep sign.
4. Overlapping-window count vs independent episodes: report both.
A pass that fails any of these is downgraded to "fragile".
