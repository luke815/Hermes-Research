# P3 pre-registration

Committed before any cell is scored. The rule is taken from research/PAIR_TRADING.md section P3 and is not varied.

## Hypothesis

A pair whose spread z-score is stretched, and that is cointegrated on the trailing window, reverts; a pair whose 30-day return spread is in the top decile continues. Both are scored on the forward return of the spread, net of costs and carry.

## Rules

Reversion. Enter when the trailing 90-day z-score of the beta-neutral spread crosses beyond 2: long the cheap leg, short the rich leg. Exit when the z-score crosses 0, at 30 days, or at a stop of 2.5 daily spread volatilities against the position. A pair is eligible only when the trailing 90-day Engle-Granger test has p below 0.05 and the half-life is between 3 and 30 days.

Relative strength. Enter the top-decile 30-day spread in the direction of the spread, beta-neutral, hold 10 days or exit on a 20-day spread reversal, stop at 2.5 daily spread volatilities.

Variants named in the spec (z thresholds 1.5 and 2.5, dollar-neutral, no cointegration filter, sector-only, 14-day window, vol-neutral) are reported beside the pre-registered rules and are not used for the verdict.

## Target

The spread return from entry to exit, both legs, signed by the position. The hedge ratio is the trailing regression of the long leg on the short leg, estimated on the 90 days before entry and held fixed for the trade.

## Periods

regime_tester/periods.py: train through 2024-06-30, validation 2024-07-01 through 2025-12-31, test from 2026-01-01. A trade is counted in the period its entry bar falls in.

## Costs

regime_tester/costs.py: taker fee and slippage on both legs, tiered by the open interest known at entry, and funding carry summed over the days held. A missing carry drops the trade rather than counting as zero.

## Pass rule

A rule is admitted only if its net spread keeps its sign in train, validation and test, the validation t-stat on non-overlapping trades reaches 2, and the independent count reaches 40. Below that bar the verdict is insufficient, not rejected. One rule being admitted does not admit the other.

## Universe

The point-in-time panel, one venue per coin among names clearing the open-interest floor on at least 60 days, the same universe the cross-section sweep scores. Pairs are every name against BTC and ETH. The screen in pairs_board is a filter, not the sample.
