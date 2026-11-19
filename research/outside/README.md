# Outside research passes, 2026-11-18

Two independent passes run from the public dashboard file and from Laevitas, with their own harness, outside
Hermes's pipeline. Nothing here is a signal. Each pass pre-registered every cell before scoring and kept the
results, so the counts of what was tried are honest.

- SIGNAL_PASS_2026-11-18.md: 202 single-threshold return cells, 9 families, dashboard data. 1 passed, failed refutation.
- OPTIONS_RISK_PASS_2026-11-18.md: options by tenor from 2019, positioning overlays, hourly, every cell also scored
  as a risk-off dial (forward drawdown, 10% crash probability, false alarms). ~650 daily cells, 0 passed.
- PREREG.md, PREREG2.md: the pre-registrations, with the risk addendum and one amendment recorded before scoring.
- harness/harness.py: event test (three periods, Newey-West t, independent episodes, costs per leg, carry by side),
  18-alt cross-section test, NaN-safe rolling percentile (a missing day returns NaN, never 0).
- harness/harness2.py: conditioned cells with parent and lift, excess (drift-controlled) spreads, hourly bars, and
  the RISK targets: forward max drawdown, crash lift, false-alarm rate, forward realized vol, left tail. R1 (the
  risk dial) should adopt these targets rather than mean return.
- harness/build_panel2.py: merges the Laevitas CSVs into a daily and an hourly panel.
- ../../results/outside_2026-11-18/: every cell's JSON, as saved by the harness.
- ../../data/outside_laevitas/: the Laevitas pulls (gzipped CSV): 25d skew / risk reversal / butterfly / ATM IV by
  tenor 2019-03..2026-11 for BTC and ETH, DVOL, IV/RV by tenor, put/call OI ratio (to 2025-03/06), options OI (to
  2024-12), futures OI by margin, perp funding and OI, and two years of hourly options and prices. COVERAGE.md
  lists first/last dates and gaps. L9 can start from these instead of re-pulling.

Run: python3 research/outside/harness/harness.py (prints a demo cell). The harness expects data/daily.pkl built from
the dashboard file; build_panel2.py builds daily2.pkl/hourly.pkl from the CSVs.

Findings that matter for the research direction:
1. Crowded-long readings (funding, futures OI, perp OI, basis at their highs) were followed by SHALLOWER drawdowns
   than average in 2021-2025 on both BTC and ETH (perp funding decile t +2.9 to +3.6, crash lift 0.4-0.7). They are
   not a sell signal on this data. Do not spend R1 effort on them as risk-off inputs without new evidence.
2. The one overheating reading with deeper drawdowns in train and test on BTC is the long/short ratio top quintile
   (Q1 below). Validation is flat; 11-19 episodes.
3. In 2026 every options extreme, puts bid or calls bid, was followed by a bounce on both assets: a single regime,
   not a direction read. A one-year test period cannot confirm what validation suggests.
4. 1-3 day alt reversal has a real rank correlation (+0.04, t 3) that two legs of costs more than remove, and it
   went negative in 2026 in every variant.

## Pass 3, 2026-11-19
PREREG3.md (pre-registered, two dated amendments) and PASS3_2026-11-19.md. Harness additions: harness/harness3.py
(TD Sequential on closes, days-in-state, exit flags, 3D/4H bars), harness/score3.py (families R1-R5), harness/base_rates.py
(builds base_rates.json for the dashboard State tab). harness/harness2.py now benchmarks a flag against the bars where
its signal exists (fix of 2026-11-19; see PASS3 report). Results and the refutation scripts: results/outside_2026-11-19/.
Nothing passed and survived refutation; the deliverable is the State tab and the method notes.
