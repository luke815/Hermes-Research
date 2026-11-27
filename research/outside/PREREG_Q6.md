# Q6 pre-registration

Committed before any cell is scored.

Hypothesis: 14-day cross-sectional momentum earns a positive spread on the
survivor-free universe, and the rank information coefficient agrees with the
spread. The outside pass found the two disagreeing on 18 names, so the
question is whether they agree on the wide universe.

Panel: data/panel_xs_laevitas. A name is in on a date only when it has a
close that date, so a name that listed later is absent rather than filled. A
name whose close moves more than 95% down or 500% up in one day is a
contract rescale and is dropped.

Rule: the signal at a weekly rebalance date is the trailing 14-day return,
lagged one bar. The book is long the top decile and short the bottom decile,
held for 5 days, then rebalanced. A decile needs at least ten names. Costs
are 15 bps per leg, charged on entry and on exit, so 60 bps round trip on
the spread. Carry is the funding rate over the five days, charged to each
leg; a date whose decile has a name with no funding value is dropped rather
than treated as zero carry.

The rank IC is the Spearman correlation between the lagged 14-day return and
the 5-day forward return, on the same dates, reported beside the spread.

Periods, fixed and never moved: train through 2024-06-30, validation
2024-07-01 through 2025-12-31, test from 2026-01-01.

Pass: the net spread and the IC keep the same sign as each other in
validation and in test, and that sign holds in both periods. A disagreement
between the spread and the IC, or a sign flip between periods, is rejected.
Fewer than 40 independent rebalance dates across train and validation is
insufficient.
