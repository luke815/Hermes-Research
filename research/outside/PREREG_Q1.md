# Q1 pre-registration

Committed before any cell is scored. The pooled panel is not scored in the
run that commits this file: reading 5,538 files did not finish inside a
research run, and the pooled part is left for the next run.

Hypothesis: a long/short ratio at its own trailing one-year high marks retail
crowding that precedes deeper drawdowns.

Panel: data/panel.csv for price, data/laevitas/market derivs_summary does not
carry the long/short ratio, so the ratio comes from data/panel_xs_laevitas,
one file per asset, the venue with the most days. Assets: BTC and ETH. The
pooled panel is not in this file's run.

Rule: the feature at date t is the trailing 365-day percentile rank of the
long/short ratio, the current bar excluded, minimum 252 bars, lagged one bar.
The flag is that rank at or above 0.8. Windows: the forward drawdown over 10,
20 and 30 days.

Targets, per window and per period:

- drawdown effect: the mean forward maximum drawdown on flagged days minus the
  mean on all days where the signal is defined. A negative number is a deeper
  drawdown.
- crash lift: the share of flagged days whose forward maximum drawdown is at
  least 10 percent, divided by the same share on all defined days.
- false-alarm rate: the share of flagged days whose 20-day forward return was
  positive.

Episodes are runs of consecutive flagged days, and the count is reported per
period. A window with fewer than 20 episodes across train and validation is
insufficient.

Pass: the drawdown effect keeps its sign in validation and in test, the
episode count across train and validation is at least 20, and the same sign
holds on both assets. A sign flip is rejected. Below the count is
insufficient. The pooled panel, when it is scored, uses the same rule and the
same bar, and a verdict on BTC and ETH alone does not close the item.
