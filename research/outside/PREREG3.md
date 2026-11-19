# Pre-registration 3: overheating as a regime, longer horizons, duration and exit, TD Sequential

Written 2026-11-19 before any cell of this pass is scored. Motivation: pass 2 found that crowded-long readings
(funding, OI, basis at their highs) were followed by SHALLOWER drawdowns in 2021-2025. The owner's point: a
consistent effect in either direction is information. This pass asks (a) whether that holds at 30-90 days as a
risk-ON / trend-continuation reading, (b) whether risk rises with TIME spent in the crowded state, (c) whether the
EXIT from a long crowded state is where the drawdown is, and (d) whether TD Sequential carries information at
1D, 3D, 4H and 1H.

Data: data/daily2.pkl (2019-2026, options and positioning), data/hourly.pkl (2024-11..2026-11). 3D is every third
daily bar; 4H is every fourth hourly bar. Rules, costs, carry, periods, excess spreads, drawdown targets:
harness.py / harness2.py unchanged. Entry at lag=1 bar. Risk cells at the quintile with the decile beside, episode
bar 20 (amendment of 2026-11-18). Return cells: validation |t| >= 2.5, same excess sign in all periods, n_ind >= 30
across train+validation, validation net > 0. Hourly/4H cells are exploratory (short periods).

Risk-ON pass (from PREREG2): drawdown effect positive (shallower) in all three periods, validation |t| >= 2.5,
crash lift <= 0.6 validation and <= 0.8 test, mean 20-day return positive in validation.

## R1. Overheating as risk-on / trend continuation (daily, BTC and ETH; alt basket where funding exists)
Primaries at the quintile (0.8) and decile (0.9): perp_funding, futures_oi, perp_oi, basis, lsr (dashboard lsr_*),
and the pair perp_funding top AND futures_oi top. Return horizons 30, 60, 90 (excess, lag=1). Risk windows 30, 60, 90
(shallower drawdowns = risk-on). Also forward realized vol 30d lower than average? (reported, no verdict).
Hypothesis: crowded-long state -> positive excess 30-90d, shallower drawdowns, lower vol. 6 primaries x 2 assets.

## R2. Duration of the crowded state
days_in_state(perp_funding pct >= 0.8) buckets: 1-10, 11-30, 31-60, >60 days. For each bucket: forward 30-day
excess return and mdd_30, crash lift, per period. Hypothesis: risk rises with duration (late in the state is worse
than early). Verdict on the trend across buckets in validation (monotone and the >60 bucket worse than the 1-10
bucket in both train and validation), not on a single bucket. Same for futures_oi and basis. 3 series x 2 assets.

## R3. The exit from a crowded state
Event: first day funding percentile drops below 0.8 after >= 20 (and >= 40) consecutive days above it. Also the
exit from OI top and basis top. Targets: forward 10, 20, 30 day excess return and drawdown, crash lift. Hypothesis:
the exit precedes the drawdown (risk-off event). Mirror: exit from the crowded-SHORT state (funding pct <= 0.2 for
>= 20 days then above) -> positive. 3 series x 2 run lengths x 2 directions x 2 assets = 24 event cells, each with
return horizons 10, 20, 30 and risk windows 10, 20, 30.

## R4. TD Sequential
Flags: buy9, sell9 (setup completion), buy9p/sell9p (perfected), buy13/sell13 (countdown completion).
Timeframes: 1D (2019-2026), 3D (every third daily bar), 4H and 1H (2024-11..2026-11, exploratory).
Hypotheses (DeMark): buy setup/countdown completion -> bounce (positive excess at 1-10 bars, shallower drawdowns);
sell setup/countdown completion -> weakness (negative excess, deeper drawdowns). Horizons in bars: 1D and 3D: 1, 3,
5, 10, 20; 4H and 1H: 4, 12, 24, 72. Risk windows: 1D 10, 20, 30; 3D 5, 10 (= 15, 30 days); 4H/1H 24, 72 bars.
Assets BTC and ETH. 6 flags x 4 timeframes x 2 assets = 48 cells.
Also, informational: the distribution of forward 10-bar returns by setup count (1..9) to see whether anything happens
before 9.

## R5. Long horizons for the pass-1 and pass-2 near misses (daily, BTC and ETH)
crowded shorts (perp_funding pct <= 0.1 / 0.2) at 30, 60, 90; lsr top at 30, 60, 90 (return and drawdown);
IV/RV bottom at 30, 60; skew_30 top at 30, 60, 90. 4 cells x 2 assets.

## Count and chance
R1 36 return + 36 risk; R2 6 series-assets (bucket tables, 1 verdict each); R3 24 x (3 return + 3 risk); R4 48 x
(5 or 4 return + 3 or 2 risk); R5 8 x 3. About 220 return cell-horizons and 200 risk cell-windows on daily/3D data
plus about 150 exploratory 4H/1H rows. Roughly 6 passes by chance at |t| 2.5 across the daily set. A family counts
only when several related cells agree in sign across periods and assets.

## Refutation on any pass
lag=2; threshold neighbours; drop the best 3 validation episodes; ex-2020; for duration/exit cells, shift min_run by
+/- 10 days; for TD cells, require the non-perfected and perfected variants to agree in sign; for 3D, re-anchor the
resampling by 1 and 2 days and require the sign to hold.

## Amendment, 2026-11-19, after counting flags and before any cell was scored
Counts seen: daily TD9 buy completions BTC 31, sell 43, countdown-13 buy 20 / sell 29 over 2019-2026 (verified
against an independent vectorized count). Funding hi-state exits after 20 consecutive days above the 80th percentile:
6 on BTC; after 40 days: 2. So:
  - R3 as written is too rare to score. It is still run and reported. A hysteresis state (on at pct >= 0.8, off when
    pct < 0.6; exit = the first day off) is ADDED as a reported-only variant, labelled post-hoc.
  - Return cells at 30/60/90 days cannot reach 30 independent episodes by construction (an episode is a cluster
    separated by more than h bars). For horizons >= 30 days the episode bar is 15 across train+validation and the
    judgment is at the family level (signs across periods, assets and horizons), not a single cell.
  - Crash threshold for risk windows: -10% at W <= 30, -20% at W = 60 and 90 (a -10% dip inside 90 days is the base
    case in crypto, so the lift would be uninformative).
  - Hourly prices have 633 short gaps (mostly 1-3 hours, 2024-11..2025-07). TD counts on 1H are computed on the
    available bars in sequence (gaps skipped), 4H bars take the last available close in each 4-hour window.
  - 3D bars are every third daily close; the three anchors (offset 0, 1, 2 days) are all computed and a 3D result
    counts only if the sign holds on all three.
