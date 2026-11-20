# Pre-registration 4: de-leveraging hazard, price and coin-OI quadrants, funding persistence

Written 2026-11-20 before any cell of this pass is scored. The proposal is the
PREREG4 section of research/outside/PASS3_2026-11-19.md, which estimated the
episode counts and was not scored. This file fixes the rules. Nothing here is a
result.

## Data

data/panel.csv for BTC and ETH closes, funding and realized vol, joined to the
Laevitas market store in data/laevitas/market for DVOL and coin-denominated open
interest. A missing day stays missing; it is never filled and never treated as
zero. USD open interest is not used as a level: it restates the price. The
hourly file named in earlier passes is absent, so no cell here uses hourly bars.

## Periods, costs, errors

Train to 2024-06-30, validation 2024-07-01 to 2025-12-31, test 2026-01-01
onward. Entry at lag 1: the position is taken the bar after the flag. Costs are
the thin tier, 15 bps each way, on both legs of a spread, and funding carry is
charged by side over the holding window. A missing funding value leaves that
leg's net missing.

A cluster is assigned to the period of its first bar, so a state that crosses a
period boundary is not counted twice. Errors are computed on non-overlapping
windows, every h-th bar for an h-day horizon, and the independent count is
reported beside the spread. A cell with fewer than 30 episodes across train and
validation is insufficient, not rejected. A return spread needs at least 40
independent observations. The t bar is 2.5, the bar the previous pass used. A
sign that flips between validation and test is rejected.

## A1. De-leveraging hazard after crowded funding

State: BTC and ETH funding at or above its trailing one-year 80th percentile,
known at t. Events within the next 10 and 20 days: coin open interest down 10
percent or more over 3 days; DVOL's 5-day change at or above its trailing
one-year 90th percentile; funding percentile falling from at or above 0.8 to
below 0.5. The hazard is the share of crowded days followed by each event,
minus the same share on days that are not crowded.

Control: the same hazard split by quintile of trailing 20-day realized vol.
The crowded state passes only if its lift over the unconditional hazard keeps
its sign in validation and test inside the vol quintile it falls in, so the
result is not just "high vol precedes high vol".

## A2. Price and coin-OI quadrants

Signal at t, known from bars through t-1: the sign of the 7-day price return
crossed with the sign of the 7-day coin open interest change. Four quadrants.
Targets: the 10-day and 20-day forward excess return, and the forward maximum
drawdown over the same windows.

Control: the 7-day price return alone, split at the same dates. A quadrant
passes only if its excess over that control keeps its sign in validation and
test. A quadrant whose whole result is the price leg is the control, not a
finding.

## A3. Crowded funding with coin open interest building or leaving

State: funding at or above its trailing one-year 80th percentile, split by
whether the 7-day coin open interest change is positive or negative. Targets
as in A2, at 10 and 20 days.

Control: the A2 quadrants on the same dates, and the same split using the 7-day
change in USD open interest. The coin-OI split passes only if it keeps its sign
where the USD-OI split does not, so a result that restates the price is dropped.

## A5. Funding-state transition matrix

States: crowded (funding percentile at or above 0.8), washed (at or below 0.2,
and only on days the rate is not exactly the venue default), neutral (the
rest). The cell is the 7-day transition matrix per period: the share of days in
each state that are in each state 7 days later.

This is a base rate, not a signal. It is reported per period and per asset. It
has no pass rule and no verdict, and it is not used to admit anything.

## A6. Funding reset while price holds, against a reset with a drop

Event: funding percentile falls from at or above 0.8 to below 0.5 within 5
days. Split by whether the 5-day price return over the same window is
non-negative (price holds) or negative (flush). Targets: the 10-day and 20-day
forward excess return and the forward maximum drawdown.

Pass: the two splits differ in sign in validation and in test, and each split
has at least 15 episodes across train and validation. Below that count the cell
is insufficient.

## What is not scored

A4 from the proposal, breadth of alt funding crowding, is below the bar and is
not part of this pass. No single-asset BTC or ETH top or bottom event cell is
added. No cell is scored in the commit that adds this file.
