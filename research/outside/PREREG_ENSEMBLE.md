# Pre-registration, 2026-11-19: the owner's ensemble risk score ("parts vote, count grows, threshold fires")
Written before scoring. Owner's framing: each reading gives positive or negative for price, the votes grow collectively,
and when many turn up the score crosses a threshold that gives an indication.

Inputs (BTC, daily, dashboard columns in daily2.pkl, each used only where it exists): funding (btc_funding), coin OI
(oi_BTC / btc), basis_btc, lsr_BTC, dvol_btc, skew_btc, IV/RV (atm_iv_btc / rv_btc), large-alt funding (median of 8),
trend (close vs 200-day mean), TD Sequential state (daily closes). Heat (Hermes's existing score) is the comparison only.
State per reading = fifth of the trailing-365-day percentile (lag 1); change = 20-day change of the reading, fifth of its
trailing-365-day distribution (lag 1).

Three vote rules, fixed now, votes in {-1, 0, +1}, score = mean of the available votes:
  V1 textbook levels: funding / coin OI / basis / lsr / large-alt funding top fifth -> -1 (crowded), bottom fifth -> +1 (washed);
     DVOL top -> +1 (panic), bottom -> -1 (complacency); skew top -> +1, bottom -> -1; IV/RV top -> +1, bottom -> -1;
     trend above the 200-day mean -> +1, below -> -1; TD buy setup 9 or buy countdown 13 completed within the last 5 days -> +1,
     sell completions -> -1.
  V2 turning up (owner's rule, literal): every reading's 20-day change in its top fifth -> +1, bottom fifth -> -1; trend and TD as in V1.
  V3 turning up, signed: as V2 but DVOL, skew and IV/RV rising -> -1 (fear building) and falling -> +1.
Thresholds: score >= +0.4 positive, <= -0.4 negative, else neutral (the heat lines). Deciles of the score are also reported.

Targets: BTC forward 10 / 30 / 60-day return: mean in positive vs negative vs all days, hit rate, Newey-West t of positive
minus negative; forward 30-day max drawdown and P(10% drop) in the negative state (risk-off use); calibration by score
decile (mean 30-day return per decile; Spearman of decile rank vs mean return).
Periods: train <= 2024-06-30, validation 2024-07-01..2025-12-31, test 2026. Entry lag 1 (score known at the prior close).
Pass rule (any variant): positive-minus-negative 30-day spread with the same sign in all three periods, validation |t| >= 2.5,
at least 20 independent episodes of each state across train + validation, and decile calibration Spearman >= 0.5 in both
train and validation. Comparison: heat with the same evaluation; placebo: 200 random re-assignments of the vote signs.
