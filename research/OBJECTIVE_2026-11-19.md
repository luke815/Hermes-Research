# Objective and plan (draft for the owner to edit), 2026-11-19

## Purpose
Inform the risk decisions of a liquid-crypto book: how much BTC beta to carry over the next two to eight weeks, and when
to cut or add. The owner wants a score that says positive or negative for price, built from parts that vote, crossing a
threshold when enough of them agree. That is a legitimate design. The rule here is that it goes on the dashboard as a
dial only once it has passed a test fixed in advance; until then the dashboard shows context (the State tab) and never
a direction call.

## What "works" means (fixed now, before any further scoring)
A score or state qualifies as a dial when, on 2020-2026 split into train (to 2024-06), validation (2024-07 to 2025-12)
and test (2026), all of the following hold with entry one day after the signal:
1. at least 20 independent episodes of the positive state and of the negative state across train and validation;
2. the 30-day return spread (positive minus negative state) has the same sign in all three periods, with validation
   Newey-West |t| >= 2.5;
3. calibration is monotone: the mean 30-day return by score decile has Spearman >= 0.5 in train AND validation;
4. the negative state has a lower 30-day drawdown and a lower P(10% drop) than all days in validation and test;
5. an independent refutation (lag 2, neighbouring thresholds, drop the best 3 episodes, simpler-control check) does
   not remove it.
A score that meets 2 and 3 but not 1 is "promising, under-sampled" and is shown with its calibration table and episode
count, labelled as such. Anything less is context.

## What we know (2026-11-19)
- Passes 1-3 (single and conditioned readings of funding, open interest, basis, long/short, DVOL, skew, risk reversals,
  butterfly, term structure, IV/RV, put/call, TD Sequential on four timeframes, time-in-state, exits): nothing passes
  and survives refutation. Crowded positioning was followed by shallower drawdowns at 10-30 days in 2021-25; open
  interest highs are price highs; the long/short ratio is a level shift plus recent weakness. See PASS3_2026-11-19.md.
- The owner's alt-froth reading (alt OI above BTC OI with large-alt funding above the 1 bp default): real regime,
  mostly 2023 to early 2024 in the 20-coin universe, one episode since, never on in 2026. Context tile on the State tab.
- The ensemble vote score, three pre-registered rules (PREREG_ENSEMBLE.md, results in outside_2026-11-19/ensemble_report.txt):
  V1 textbook contrarian levels: spread flips sign between periods (+3.0 / -3.7 / -1.9 at 30 days), calibration not
  monotone. V2 "readings turning up = positive" (the owner's rule, literal): train 0, validation -3.0, 2026 -6.6%:
  the opposite sign out of sample. V3 (fear measures signed the other way): same sign in all periods (+2.7 / +2.2 / +7.1)
  but t about 0 and 2-3 episodes per period; calibration flat. None qualifies; a placebo of random vote signs reaches
  the validation bar 8% of the time, so the bar is real.
- Hermes's heat (a momentum/trend composite built on train): 30-day spread +11.3 / +9.4 / +4.7, calibration Spearman
  +0.87 / +0.78 / +0.12. Monotone in 2021-25, flat in 2026, 2-5 episodes per state in validation. Relabel on the dashboard
  as "trend composite: calibrated 2021-25, flat in 2026", not validated.

## Reading of all this
Positioning and options data describe the market's own state; over two to eight weeks BTC direction in 2024-26 has
been set by flows and macro (spot ETF flows, stablecoin issuance, dollar and real yields, equity risk appetite), which
the panel does not contain. The one composite with any calibration is the trend one. So the next step is not another
combination of the same inputs; it is adding the inputs that move price, testing each the same way, and only then a
pre-registered ensemble over the parts that individually show a stable sign.

## Plan
P1 (Hermes, one to two weeks): add daily series and backfill to 2020 where they exist: spot BTC ETF net flows
(Farside/CoinGlass), ETH ETF flows, stablecoin supply change USDT+USDC (DefiLlama, free), exchange BTC reserves and
netflow (CoinGlass or CryptoQuant), Coinbase premium (Coinbase vs Binance spot), DXY, 10-year real yield and the Fed
balance sheet (FRED, free), S&P 500 and NDX closes (free), BTC dominance. Each gets a units line in COVERAGE and a
puller with record_write.
P2 (outside, after P1): pre-register and score each new series alone at 10/30/60 days with the same rules (return,
drawdown, calibration), then the trend composite re-stated with fixed weights, then an ensemble over the parts that
showed a stable sign; refutation before anything is shown.
P3 (Hermes, in parallel): PREREG4 from the backlog P4 list (de-leveraging hazard after crowded funding, price x
coin-OI quadrants, funding reset, transition matrix) and the alt-froth reading on the all-venue top-100 intraday universe.
P4 (dashboard): if something qualifies, a dial with its calibration table and a live ledger of its calls and outcomes;
otherwise the State tab stays the product, heat is relabelled, and the ensemble is shown only as a breadth count
("how many readings are hot or cold today") with its measured 30-day hit rate next to it.

## Rules that do not change
Pre-register before scoring; no fitting of weights or thresholds on the test periods; results written by write_result
with provenance; an independent refutation before anything reaches the dashboard; the dashboard says what followed,
never what will follow, until a dial has qualified.
