# Direction, 2026-11-25: what six weeks of Hermes have shown, and what to do with it

## The record, in one paragraph
Hermes was started on 19 Oct to find regimes and signals in derivatives data. In its first three hours it produced a
vol-regime "edge", an OI-dominance "signal", a six-regime map and a continuous overheating score, all on one pass over
the same data with overlapping t-statistics; that score became "heat". By 29 Oct its own honest statistics (non-
overlapping counts, look-ahead purged) left one factor standing (30-day momentum, t 2.3 on 24 observations) and by
1 Nov the three-period split rejected every factor. From 5 Nov a sweep over roughly 300,000 indicator cells fed a
confirmation procedure: 26 confirmations rejected by 6 Nov, and a further twelve (A7 in four parts, D22, the weekly
round, G21 to G32) rejected between 20 and 25 Nov. In parallel, five outside passes (17 to 19 Nov) pre-registered about
1,800 cells over positioning, options, term structure, TD Sequential on four timeframes, an ensemble vote score, flows,
macro and BTC's own trend; nothing passed and survived refutation. The paper long/short book built from the same
pipeline is down 37 percent since 5 Nov. Four of the audit fixes from 17 Nov that the confirmer's correctness depends on
(A2, A3, A4, A6) are still open, so by Hermes's own rule the sweep verdicts since then are not evidence either way.

## What that means
At a daily close, with states defined as fifths of a trailing year, nothing in positioning, options, flows or macro has
timed BTC over 1 to 60 days across 2020-24, 2024-25 and 2026. Trend worked until 2026 and reversed. This is not a
failure of effort; it is the answer to the question as posed. Continuing to pose it costs credits daily and produces
bookkeeping (158 of 367 commits since 20 Nov were notes).

## Direction
1. Retire the signal hunt as the objective. The sweep and confirmation loop stops (disable the sweep daemon; close the
   open G items as "not evidence: A2-A4 open"). No new cells are pre-registered against daily-close timing of BTC.
2. Hermes's job becomes two things it is already good at: (a) data and operations: daily pulls, panel integrity, the
   live store, the dashboard, health; (b) description: the State tab, the relative-strength board, the pairs board,
   today's tape. Measured, never forecast.
3. Fix what misleads. The Overview "Positioning" card now shows the long/short Q1 test as "kept"; the train effect is
   zero, the crash lift is 0.0 / 1.2 / 3.4 by period, there is no recent-return control, and the cited results file is
   not committed. Relabel it "scored: 2026 carries it; control not run" or remove it. The paper book comes off the
   dashboard until its construction is re-examined. Heat stays labelled as a trend composite, context only.
4. Two bounded research questions, two weeks each, pre-registered, with a stop rule:
   R-A Regime-conditional behaviour. Define regimes without hindsight (trailing 30-day realized vol fifth, close vs
       200-day mean). Test whether momentum holds in high-vol trending regimes and reversal in low-vol chop, on BTC,
       ETH and the alt cross-section. The product is a sizing rule by regime, not a direction call; the pass rule is
       the OBJECTIVE_2026-11-19 one.
   R-B The alt board as a measured product. Keep the relative-strength and pairs boards, add a weekly ledger of what
       happened to last week's top and bottom deciles (hit rate, spread vs BTC, drawdown), published on the dashboard
       with its history. If a decile spread shows a stable sign over 12 weeks it earns a pre-registered test; if not,
       the board stays descriptive.
   Optional R-C: spot ETF flows, only if a keyed source exists. No scraping.
5. Cost and cadence. Research runs twice a day, not hourly; the hourly job is health only; no note or status scripts
   (one line in the log, not a committed script per note). Daily credit cap agreed with the owner.
6. Close the audit properly or declare it: A2, A3, A4, A6 either done with tests or marked "not done, sweep closed"
   so the record is honest about what the earlier verdicts rest on.

## What the owner gets
A dashboard that is correct about what it shows, a daily tape of where every reading sits and what followed such
states, an alt board with its own measured track record, and two research questions that can actually change how the
book is sized. Not a number that says up or down.
