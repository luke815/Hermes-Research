# Q2 pre-registration

Committed before any cell is scored.

Hypothesis: skew at its own trailing high while implied vol sits at its own
trailing low marks a market that is positioned for a move it is not paying
for, and that state precedes weakness.

Panel: data/laevitas/market, skew_25d for the 30-day tenor and dvol, one row
per UTC day, the last row that names the day. Assets: BTC and ETH. Price from
data/panel.csv.

Rule: the feature at date t is the trailing 365-day percentile rank of each
series, the current bar excluded, minimum 252 bars, lagged one bar. The flag
is skew's rank at or above 0.9 and dvol's rank at or below 0.2, both on the
same day. Horizons: the forward return at 5, 10 and 20 days. Drawdown
windows: the forward maximum drawdown over 10 and 20 days.

This is a new hypothesis, so the sign is confirmed only on the two fresh
windows: 2019-03 to 2020-01, and 2026. The years 2020 to 2025 are reported
and are not used for the verdict.

Targets, per horizon and per window:

- return effect: the mean forward return on flagged days minus the mean on
  all days where the signal is defined. A negative number is weakness.
- drawdown effect: the mean forward maximum drawdown on flagged days minus
  the mean on all defined days. A negative number is a deeper drawdown.

Episodes are runs of consecutive flagged days, and the count is reported per
window. A window with fewer than 20 episodes is insufficient.

Pass: the return effect keeps its sign in both fresh windows, the episode
count in each fresh window is at least 20, and the same sign holds on both
assets. A sign flip between the two fresh windows is rejected. Below the
count is insufficient. The 2020 to 2025 rows are reported and are not the
verdict.
