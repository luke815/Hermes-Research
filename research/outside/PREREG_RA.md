# Pre-registration R-A: regime-conditional momentum and reversal, 2026-11-26

Written before any cell is scored. The one robust finding of passes 1-5 is that 2026 behaves differently: trend
continuation (BTC 20-day return, close vs 50-day mean) was calibrated in 2020-24H1 and 2024H2-25 and reversed in
2026, and so did Hermes's heat. This pass asks whether that is a regime effect that can be identified WITHOUT
hindsight, so that the book's sizing can follow the regime rather than a direction call.

## Regimes (known at the prior close, no hindsight)
vol: trailing 30-day realized vol of BTC, fifth of its trailing 365 days (low = bottom two fifths, high = top two fifths).
trend: BTC close above or below its 200-day mean, and the 200-day mean rising or falling over 20 days.
Four regimes: calm-up, calm-down, wild-up, wild-down (calm = low vol, wild = high vol, up/down = above/below the mean
with the mean's slope agreeing; mixed states are "other" and reported, not scored). Occupancy and persistence of each
regime (P(same regime 14 days later)) are reported first; a regime with fewer than 15 independent episodes across
train and validation is not scored.

## Cells
Within each regime, the same three readings as PREREG5's trend addendum, scored on BTC and ETH at 10 and 30 days:
  btc_ret20 top fifth -> continuation (+), bottom fifth -> continuation (-)     [momentum]
  btc_ret5  top fifth -> reversal (-), bottom fifth -> reversal (+)              [short-term reversal]
  close vs 50-day mean, above -> +, below -> -                                   [trend state]
and on the alt cross-section (data/panel_xs, point in time, $20M OI floor): rs30 top minus bottom decile over the
next 7 days (the ALT_LS_PREREG rule) within each regime.
Hypothesis, fixed now: momentum and trend hold in the wild regimes and fail or reverse in calm-down; short-term
reversal holds in calm regimes. If the signs do not line up this way the hypothesis is rejected whatever the t-stats.

## Rules
Entry lag 1; excess vs all days of the same regime and period (so a regime's own drift is not credited); costs and
carry as in harness2; Newey-West t at lag h; independent episodes; periods train to 2024-06-30, validation
2024-07-01 to 2025-12-31, test 2026. A regime x cell passes when the sign agrees with the hypothesis in all three
periods with >= 3 episodes each, validation |t| >= 2.5, and >= 20 episodes across train + validation. The product of a
pass is a sizing table (regime -> which of momentum / reversal / neither carried) with its calibration, not a signal.
Count: 4 regimes x 6 BTC/ETH cells x 2 horizons + 4 cross-section cells = 52 cells; about 1 chance pass at 2.5.

## Refutations on any pass
Regime boundaries moved one fifth; the 100-day mean instead of the 200-day; drop the best 3 validation episodes;
the regime defined on ETH instead of BTC; lag 2.

## Done when
results/<date>_ra_regimes.json carries occupancy, persistence and episode counts per regime and period, written by a
committed script through write_result; results/<date>_ra_cells.json carries every cell with its verdict; the verdict
line in research/log.md names the regimes that carried momentum, reversal or neither, or says none did.
