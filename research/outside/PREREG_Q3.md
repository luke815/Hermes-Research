# Q3 pre-registration

Committed before any cell is scored.

Hypothesis: implied vol cheap against realized vol marks a market that is not
paying for the moves it has just had, and that state precedes weakness and
deeper drawdowns. The question is whether the 2026 reversal is the rule or
the exception.

Panel: data/laevitas/market, the iv_rv series, one row per UTC day, the last
row that names the day. The ratio is iv_30 divided by rv_30. Assets: BTC and
ETH. Laevitas serves per-coin implied vol for those two only, so no broader
universe is scored; inventing the ratio for names without it would score the
gap. Price from data/panel.csv.

Rule: the feature at date t is the trailing 365-day percentile rank of the
ratio, the current bar excluded, minimum 252 bars, lagged one bar. The flag
fires when that rank is at or below 0.1.

Horizons: the forward return at 10 and 20 days. Drawdown windows: the forward
maximum drawdown over 10 and 20 days.

Periods, fixed by the research program and never moved: train through
2024-06-30, validation 2024-07-01 through 2025-12-31, test from 2026-01-01.
The 2026 rows are reported beside the 2020-2025 rows, and 2026 is the test
period, so it is not used to choose the rule.

Episodes are runs of consecutive flagged days. A cell with fewer than 20
episodes across train and validation is insufficient.

Pass: the return effect and the drawdown effect each keep their sign in
validation and in test, on both assets, with the episode bar met. A negative
number is weakness or a deeper drawdown. A sign flip between validation and
test is rejected. Below the count, or a missing effect, is insufficient.
