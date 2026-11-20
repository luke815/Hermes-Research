# Pre-registration, 2026-11-19 (owner's hypothesis): alt froth = alt OI above BTC OI with large-alt funding hot
Written before scoring. Owner's words: "Alt OI > BTC OI + some variation of funding rates of larger alts being > certain level"
was what used to work best. Data limit: the dashboard universe is BTC, ETH and 18 alts; alts alone never exceed BTC OI
here (0.31-0.85x), alts plus ETH do on 33% of days. Definitions (dashboard columns, 2022-09-09 onward):
  alt_oi_ratio = (oi_ETH + sum of the 18 alt oi_*) / oi_BTC                 (A: ratio > 1)
  bigalt_funding = median funding of BNB, SOL, XRP, ADA, DOGE, LINK, AVAX, DOT, percent per 8h   (B: > 0.01, i.e. above the 1 bp default)
  froth = A and B. Variants reported: A alone, B alone, A and bigalt_funding pct365 >= 0.8, alt_oi_ratio pct365 >= 0.8 and B.
Targets: BTC forward 10/20/30-day excess return and forward max drawdown (10/20/30), crash lift; alt basket (alt_price)
relative to BTC over 10/20/30 days. Hypothesis: froth -> BTC weaker, deeper drawdowns, alts underperform BTC.
Periods as always (train <= 2024-06-30 is only 2022-09..2024-06 here, so this is two short periods plus 2026). Entry lag 1.
Pass rule: same sign in all periods with >= 3 episodes each, validation |t| >= 2.5, episode bar 20 across train+validation
for risk cells; otherwise reported as a base rate only.
