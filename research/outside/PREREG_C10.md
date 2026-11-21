# C10 pre-registration

The weekly cycle layer. Copied from research/RESEARCH_PROGRAM_CYCLE.md section 4, which says the weekly layer is the same procedure on weekly bars with horizons of 12 and 26 weeks, and the sample size is stated plainly because there are only a handful of cycle tops and bottoms.

Hypothesis: a weekly close at its own trailing extreme precedes a cycle top or a cycle bottom over the next 12 and 26 weeks. The sample is thin by construction, and a cell that does not reach the episode bar is insufficient, not a signal.

Panel: the daily close panel, resampled to the weekly close taken on Sunday. BTC and ETH are scored separately. A pooled panel is not scored: the cycle spec's pooled panel needs SOL and the ten largest alts, and no point-in-time weekly panel of those names is on disk.

Rule: the signal at week t is the prior week's close divided by its trailing 52-week high, so week t itself never enters. A top flag is that ratio at or below 0.05, which is a weekly close within 5 percent of its trailing high. A bottom flag is the same ratio at or above 0.40, which is a weekly close at least 40 percent below its trailing high. The first 52 weeks are empty.

Target: the forward label starting after week t. A top is the lowest weekly close in the next h weeks at least 25 percent below this week's close. A bottom is the highest weekly close in the next h weeks at least 30 percent above this week's close, with no weekly close in the window more than 10 percent below it. Horizons 12 and 26 weeks. Both labels look forward and are never features.

Periods: train to 2024-06-30, validation 2024-07-01 to 2025-12-31, test 2026-01-01 onward, applied to the week-ending date.

Pass: the lift keeps its sign in validation and in test, and the episode count across train and validation is at least 30. Below 30 episodes is insufficient, whatever the lift. A sign flip is rejected. The weekly sample size is reported beside every cell. Neighbours, scored and reported but not used for the verdict: the same flags at a 26-week trailing high instead of 52.
