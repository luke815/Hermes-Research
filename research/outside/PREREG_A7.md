# A7(2), A7(3), A7(4) pre-registration

Committed before any cell is scored. A7(1) is already pre-registered in
research/backlog.md at commit 2d78832 and is blocked on a bad close in
data/panel_xs_laevitas, which a research run does not rewrite. These three
parts use data already on disk.

Periods for every part: train through 2024-06-30, validation 2024-07-01 to
2025-12-31, test from 2026-01-01. Every feature at bar t uses only bars before
t. The target is the forward return starting at today's close. t-stats use
non-overlapping windows, every h-th bar for an h-bar horizon, and the
independent count is reported beside the spread.

## A7(2) derivatives family, BTC and ETH

Hypothesis: the options and positioning state of BTC and ETH predicts the next
1 to 3 days of return, and the same state tells whether the cross-sectional
reversal in A7(1) works.

Panel: data/laevitas/market for the options series, data/panel.csv for price
and funding. One row per UTC day, the last row that names the day.

Features, each lagged one bar, on BTC and on ETH separately:

- skew: the 30-day tenor of skew_25d, as a trailing 365-day percentile rank
  with a minimum of 252 bars, and as a 5-day change.
- risk reversal: the 30-day tenor of risk_reversal_25d, same two transforms.
- implied minus realized: iv_30 minus rv_30 from iv_rv, same two transforms.
- basis: the 30-day tenor of oi_weighted_basis, same two transforms.
- funding: btc_funding and eth_funding from data/panel.csv, same two transforms.
- open-interest change: the 7-day percent change in open_interest from
  derivs_summary, same two transforms.

Rule: the extreme is the top quintile of the trailing percentile rank (at or
above 0.8) and, separately, the bottom quintile (at or below 0.2). The 5-day
change is split the same way on its own trailing percentile rank. Both splits
are reported. The book is long the asset when the feature is in the top
quintile and flat otherwise, and short the asset when it is in the bottom
quintile and flat otherwise. Each side is scored on its own.

Target: the asset's own forward return at 1 day and at 3 days, minus a 15 bps
round trip, minus the asset's own funding carry over the holding window. A
missing funding value leaves the net missing; it is not treated as zero.

Filter on A7(1): not scored in this run. A7(1) has no verdict, and a filter on
a score that is not a verdict would be a verdict on nothing. The filter is
left for the run that rescores A7(1) after the close is corrected.

Pass: the spread keeps its sign in validation and in test, the non-overlapping
t-stat is at least 2 in both, and the independent count is at least 40 in
each. Below the count is insufficient. A sign flip is rejected. A cell that
passes on one asset and fails on the other is insufficient. Neighbours,
scored and reported but not used for the verdict: the same rule at the 7-day
and 90-day tenors where the store has them.

## A7(3) pooled crowding before alt tops

Hypothesis: open interest stretched against volume, and a fast build in open
interest, precede damaging drawdowns in the alt basket. The earlier lead was
on five names; this scores the pooled basket with errors clustered by date.

Panel: data/panel.csv alt_price for the basket, data/laevitas/market
derivs_summary for ADA, SOL, LINK, XRP and AVAX. The basket price is the
equal-weight series already in the panel, which is survivor-biased, and the
result says so.

Features, each lagged one bar, per name and pooled:

- oi_over_volume: open_interest divided by volume, both from derivs_summary,
  at or above its own trailing 365-day 90th percentile, minimum 252 bars.
- oi_change_30d: the 30-day percent change in open_interest, at or above its
  own trailing 365-day 90th percentile, minimum 252 bars.

Label: the amended top event T(30, 20) from regime_tester.episodes, restricted
to candidate days within 5 percent of the trailing 60-day high, the extreme
taken from past bars only, as cycle_score.candidate_mask does. The label looks
forward and is never a feature.

Target: the lift, which is the share of flagged candidate days whose label is
true divided by the share of all candidate days whose label is true, and the
forward 10-day return of the basket net of a 15 bps round trip. Errors are
clustered by date: one observation per date, the pooled flag being true when
at least three of the five names are flagged that day.

Pass: the lift is above 1 in validation and in test, the clustered
non-overlapping t-stat on the return is at least 2 in both, and the
independent count is at least 40 in each. Below the count is insufficient. A
lift below 1 in either held-out period is rejected. The per-name rows are
reported and are not the verdict.

## A7(4) top-decile funding against forward returns

Hypothesis: coins paying the most funding underperform coins paying the least
over the next 1 and 3 days, after the carry is charged, and the edge is not an
illiquid-name effect.

Panel: data/panel.csv, the market-level series. The cross-sectional panel is
not used, because A7(1) showed that one bad close in it dominates a decile
spread, and a research run does not rewrite that panel.

Rule: the signal at date t is the negative of the funding rate on the prior
bar. The book is long the name with the lower funding and short the name with
the higher funding, equal weight, rebalanced daily. Both legs are always
present, so there is no decile and no floor.

Target: the forward return starting at today's close, horizons 1 and 3 days,
minus BTC's return over the same window. Net of a 15 bps round trip on each
leg and of each leg's funding carry over the holding window. A missing funding
value leaves that leg's net missing.

Pass: the spread keeps its sign in validation and in test, the non-overlapping
t-stat is at least 2 in both, and the independent count is at least 40 in
each. Below the count is insufficient. A sign flip is rejected. This part is
two names, so it is reported as a market-level reading and cannot by itself
close A7(4)'s cross-sectional clause.
