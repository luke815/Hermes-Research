# Pre-registration 2: options tape, term structure, positioning overlays, multiple timeframes

Written 2026-11-18 before any cell of this pass is scored. Builds on PREREG.md; the first pass found no single-threshold
signal at 1-10 days on the dashboard file. This pass asks whether the options market carries conditional or
term-structure information that a single blended series missed, and whether it works at other horizons.

## Data (pulled from Laevitas, Deribit options, Binance perps)
Daily from 2019 where served: 25d skew by tenor (7/14/30/60/90/180/365), 25d risk reversal by tenor, 25d butterfly by
tenor, ATM IV by tenor, DVOL, IV/RV, put/call OI ratio, options OI total, futures OI total, perp funding, perp OI.
Hourly for the last two years: DVOL, skew/RR/ATM IV by tenor, perp price, funding, OI where served.
Prices: daily from the dashboard file (BTC, ETH); hourly from Binance perps.

## Periods
Daily: train <= 2024-06-30 | validation 2024-07-01..2025-12-31 | test >= 2026-01-01 (as before). Series that start in
2019 add about two years of train versus the first pass.
Hourly (two years only): train 2024-11..2025-06 | validation 2025-07..2025-12 | test 2026. Short, so hourly results are
reported as exploratory unless they also hold on daily data.

## Fixed rules
Entry at lag=1 bar (the position is taken one bar after the signal bar closes). lag=0 reported only as an upper bound.
Primary thresholds: trailing-365-day percentile >= 0.9 / <= 0.1 (daily); trailing-90-day percentile for hourly
(>= 0.9 / <= 0.1). Conditioner thresholds: percentile >= 0.8 / <= 0.2. No other thresholds are tried.
Horizons: daily 1, 3, 5, 10, 20; hourly 4, 12, 24, 72 bars.
Statistics, costs, carry, independent-episode counts: harness.py, unchanged. Drift control: every spread is also
reported against the same-period mean (excess), and the verdict uses the excess version.

## Pass rule for this pass (stricter than pass 1, because there are more cells)
Single cells: same sign of the excess spread in all three periods; validation |t| >= 2.5; test same sign;
n_ind >= 30 across train+validation; validation net > 0 at lag=1.
Conditioned cells (primary AND conditioner): all of the above, AND the unconditioned primary cell has the same sign in
validation, AND the conditioned lift (conditioned spread minus unconditioned spread) is positive in train AND validation.
A conditioned cell whose parent points the other way is interaction mining and is reported as such.
Everything else: insufficient or rejected.

## Families and cells
H1. Term structure of fear (BTC and ETH, daily)
  - skew term slope = skew_7 - skew_90: pct top (front-end panic) -> up over 3-10d; pct bottom -> down
  - ATM term slope = atm_iv_7 - atm_iv_90: pct top (inverted, front-end stress) -> up over 3-10d; inversion flag (slope > 0) -> up
  - butterfly_30 pct top (tail demand both sides) -> large move either way: report |return| spread and the signed spread
  - skew_7 pct top vs skew_90 pct top: which tenor carries information (report both)
H2. Direction of the options market (new hypotheses, confirmed only on data pass 1 never used for sign: 2019-2020 and 2026)
  - puts bid: skew_30 pct top -> DOWN over 5-20d; rr_30 pct bottom -> DOWN
  - calls bid: skew_30 pct bottom -> UP; rr_30 pct top -> UP
  - DVOL pct top -> DOWN over 5-20d (fear is right, not contrarian)
  - fast repricing: skew_30 1-day change z30 >= 2 -> DOWN over 1-5d; <= -2 -> UP
H3. Positioning overlays (daily; conditioners at 0.8/0.2)
  Primary cells from H1/H2 and from pass 1's F3 (funding bottom decile -> up), each crossed with ONE conditioner:
  - futures_oi pct >= 0.8 (leverage high) / <= 0.2
  - options_oi pct >= 0.8 / <= 0.2
  - put/call OI ratio pct >= 0.8 (hedged) / <= 0.2 (unhedged)
  - perp funding pct >= 0.8 (crowded long) / <= 0.2 (crowded short)
  - trend: close above / below its 50-day mean
  Specific pre-registered combinations (the ones with a story), 1 conditioner each:
  a) skew_30 top AND futures_oi top -> DOWN (fear plus leverage = forced selling ahead)
  b) skew_30 top AND futures_oi bottom -> UP (fear with no leverage = washed out)
  c) DVOL top AND funding bottom -> UP (panic plus crowded shorts)
  d) DVOL bottom AND futures_oi top -> DOWN (complacency plus leverage)
  e) funding bottom AND trend up -> UP (crowded shorts in an uptrend)
  f) funding bottom AND trend down -> report; sign unknown
  g) pc_ratio top AND skew top -> UP (fully hedged market rarely crashes)
  h) pc_ratio bottom AND DVOL bottom -> DOWN (unhedged and complacent)
  i) ATM inversion AND futures_oi top -> DOWN
  j) butterfly top AND futures_oi top -> |return| large
  k) skew_30 top AND DVOL top -> DOWN (both fear measures agree) vs skew_30 top AND DVOL bottom -> UP (skew without vol: hedging, not panic)
  l) rr_30 bottom AND pc_ratio top -> UP
H4. Vol regime (daily)
  - IV/RV ratio pct top -> UP over 5-20d (options overpriced, realized calm follows) ; bottom -> DOWN
  - IV/RV ratio pct top AND trend down -> UP (capitulation priced)
  - DVOL 5-day change pct top (vol shock) -> report 1-5d and 10-20d separately
H5. Hourly (exploratory; BTC and ETH)
  - DVOL 1h pct90 top -> UP over 24-72 bars; skew_30 1h pct90 top -> DOWN over 12-72 bars; rr_30 1h pct90 bottom -> DOWN
  - skew_30 1h change over 4 bars z (90d) >= 2 -> DOWN over 4-24 bars
  - funding 1h pct90 bottom -> UP over 24-72 bars (if hourly funding is served)
  - OI 1h 24-bar % change pct90 top -> report
H6. Alt cross-section revisited with conditioning (18 alts, daily; the data limit stands)
  - 1-3 day reversal ONLY on days when BTC DVOL pct >= 0.8 (reversal is stronger in high-vol regimes): net after 30 bps per leg
  - 1-3 day reversal ONLY when BTC futures OI dropped > 5% in 3 days (post-flush)
  - 14-day momentum ONLY when DVOL pct <= 0.5 (calm regimes)

## Count
H1 8 cells x 5 horizons = 40; H2 8 x 5 = 40; H3 12 x 5 = 60 (+ the parent cells already in H1/H2/F3); H4 4 x 5 = 20;
H5 6 x 4 x 2 assets = 48; H6 3 x 3 = 9. About 217 cell-horizons, roughly 11 passes expected by chance at |t| 2, about
3 at |t| 2.5. A family is credible only when several related cells agree and the conditioned lift is consistent.

## Robustness on any pass
lag=2; neighbouring thresholds (0.85/0.95; conditioner 0.75/0.85); drop the best 3 validation days; ex-2020; and for
conditioned cells, swap the conditioner for its neighbour (futures_oi -> options_oi) and check the sign holds.

## Addendum, written 2026-11-18 before scoring: RISK targets (the owner's actual use is a risk-off dial)

The question for a portfolio manager is not "does this earn after costs" but "when this fires, is the downside ahead
worse than usual". So every primary and conditioned cell in H1-H4 (daily) is also scored against risk targets, on
BTC and ETH, with the SAME flags and periods:

Targets per signal bar t (position already held; the decision is to cut or keep):
  mdd_W   forward maximum drawdown over the next W bars: min over k<=W of close[t+k]/close[t] - 1, W in 10, 20, 30
  crash_W event: mdd_20 <= -10% (and -15% reported), W = 20
  rv_20   realized vol over the next 20 days (annualized)
  q05_20  5th percentile of the 20-day forward return among flagged bars vs among all bars
  missed  mean 20-day forward return on flagged bars (what you forgo by being risk-off) and the share of flagged
          bars with a positive 20-day return (false-alarm rate)

Statistics: mean mdd_W on flagged bars minus on all bars (negative = worse), Newey-West t with lag W; crash lift =
P(crash | flag) / P(crash) with the counts; AUC of the continuous signal for the crash event (rank-based, per period);
n_ind as before.

Pass rule for a RISK-OFF cell: mdd_20 difference negative in all three periods; validation |t| >= 2.5 on mdd_20;
crash lift >= 1.5 in validation AND >= 1.2 in test; n_ind >= 30 across train+validation; and the false-alarm rate in
validation below 60% (if most flagged periods still ended higher, the dial costs more upside than it saves).
A RISK-ON cell (washed-out, buy-the-dip) passes on the mirror: mdd_20 difference positive (shallower drawdowns), crash
lift <= 0.6 in validation and <= 0.8 in test, and mean 20-day return positive in validation.

Dial (only if at least two independent risk-off cells pass): equal-weight sum of the passing cells' flags, mapped to
0-100; its calibration table (dial bucket -> crash rate, mean mdd_20) is reported per period. Nothing is fitted; the
weights are equal by rule, so there is no in-sample tuning of the dial.

Added cells (risk-specific, daily, BTC and ETH): crash_W is also tested against the obvious "overheating" candidates
from pass 1 that failed on returns: funding pct top (crowded longs), futures/perp OI pct top, basis pct top,
lsr pct top, DVOL pct bottom (complacency), IV/RV pct bottom, pc_ratio pct bottom (unhedged), and the pairs
funding top AND OI top, DVOL bottom AND OI top, basis top AND funding top. 13 primary + 3 pairs, 2 assets, 3 windows.
Count: about 96 risk cell-windows on top of the 217 return cells. Roughly 3 risk passes expected by chance at the
2.5 bar; a credible dial needs agreement across windows and assets, not a lone cell.

## Amendment, 2026-11-18 14:40 UTC, after one smoke cell (skew_30 top, BTC) and before any family was scored
The 30-independent-episode bar from pass 1 was set for 1-10 day horizons. At 20-30 day drawdown windows, decile
extremes over 2020-2025 produce 7-18 episodes by construction (an extreme that lasts weeks is one episode), so the
risk cells would all be "insufficient" whatever the data said. For RISK cells only:
  - the primary threshold is the quintile (pct >= 0.8 / <= 0.2); the decile is reported beside it as the sharper cut;
  - the episode bar is 20 across train+validation, separation W bars, and the exact counts are always printed;
  - a risk cell that passes only at the quintile and not at the decile is labelled "broad", one that passes at both
    "sharp", and the dial uses only cells that are at least broad in both BTC and ETH or in two windows.
Return cells keep the pass-1 rules unchanged. This amendment was written before the risk families were scored; the
smoke cell seen (skew_30 top on BTC, decile) showed train mdd -3.8% t -1.4 and nothing out of sample.
