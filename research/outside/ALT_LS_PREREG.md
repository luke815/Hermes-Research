# Pre-registration: the alt long/short board, 2026-11-26

Written before scripts/alt_ls_board.py was run on any data. The owner's question is "which alts are the best longs and
shorts to take". The honest product is a fixed ranking rule, its full-history record and a live weekly ledger, shown
together, so the board is judged by what it did and not by what it claims.

## Rule (fixed)
Universe: every name in data/panel_xs with a year of closes, listed today, crypto only (no tokenized stocks, ETFs,
indices or commodities), open interest at or above $20M and 24-hour volume at or above $15M from data/universe.csv.
BTC and ETH are benchmarks, not members.
Signal at the Monday close: rs30 = the name's 30-day return minus BTC's 30-day return. Crowding: the funding rate's
trailing-365-day percentile.
Longs: the top decile by rs30 whose funding percentile is below 0.8. Shorts: the bottom decile by rs30 whose funding
percentile is above 0.2. Equal weight, entered at the close after the Monday close (lag 1), held 7 days. Costs 30 bps
round trip per name, funding carry charged by side over the hold.
Reported beside it, not traded: the unfiltered decile spread, rs7 (the 7-day relative return) and the 30-day open
interest change for each name.

## Hypothesis
Cross-sectional 30-day relative momentum among liquid alts carries forward over the next week (the long basket beats
BTC, the short basket lags BTC), and the funding filter removes the most crowded names on each side without removing
the effect. The literature supports 1-3 month cross-sectional momentum in crypto; Hermes's own A7(1) rejected 1-3 day
reversal and G24 (12-day rate of change) failed out of sample, so the 30-day horizon is a hypothesis, not a result.

## What is measured
History: for every Monday with a year of data behind it, the long basket, the short basket and the spread, net of
costs and carry, in weekly non-overlapping rows; mean, hit rate and t per period (train to 2024-06-30, validation
2024-07-01 to 2025-12-31, test 2026). The board carries the agreement of the spread's sign across the three periods.
Ledger: from the first week the script runs, each week's lists and their realized 7-day relative returns, filled when
the hold ends; cumulative hit rate and mean by side.

## Pass rule for calling it more than a ranking
The weekly spread has the same sign in all three periods with validation |t| >= 2.5 and at least 40 weeks in
train + validation, and the 2026 hit rate is above 0.5 over at least 20 weeks of the live ledger. Until then the board
is a ranking with its record attached. The rule is not tuned: no threshold, horizon or filter is changed on the basis
of the history; a change is a new pre-registration with a new ledger.

## Refutations to run if it passes
Lag 2; decile = top/bottom 20 percent; hold 14 days; drop the best 3 weeks; a universe without the funding filter;
the same rule on 2021-2022 only; and whether the spread is explained by beta (regress basket relative returns on BTC's
return over the hold).
