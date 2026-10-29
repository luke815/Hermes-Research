# Standing mandate

Set by Luke on 2026-10-26 and extended the same day. This file is the source of truth for the research jobs. A fresh session reads this before doing anything.

## What this is

A research engine for BTC, ETH and the alt universe. It maintains regime and pricing models and turns them into a ranked flow of short-term (1 to 3 day) and swing (5 to 20 day) opportunities, delivered to the Telegram origin. It does not trade, does not spend money, and does not put keys in chat.

## Where things stand

Heat score: seven equal-weight factors in regime_tester/heat.py, scaled -1 to +1. Hot above +0.4 has held out of sample. Cold and middle have no reliable edge and must never be dressed up as a forecast.

Pricing: rolling two-year refit on the same factors, BTC 10-day forward return. Ranking holds out of sample, top fifth +3.3% against bottom fifth +1.0%. Levels do not hold and are reported as a ranking, not a number to trust.

TA library: regime_tester/ta.py. Twelve candidates tested 2026-10-27. None admitted to the score. slope_ma20 and atr_regime widened the gap but restate momentum and volatility. They are valid standalone confirmations for the scanner.

## Admission test

No look-ahead. Walk-forward, fit on the first half and score on the second. Same sign in both halves on BTC and the alt basket. Joins a model only if it widens that model's out-of-sample gap. Report correlation with existing factors every time. No claimed edge on fewer than about 40 independent observations. Learned weights replace equal weights only when they win out of sample by a margin the sample supports.

## Jobs

- fd17d1afd23c hourly: tunnel, data freshness, regime crossings, scanner.
- 5c3cb7cde65a daily 06:30 Amsterdam: refresh, refit, ledger.
- de7edc9f00bd daily 07:00: digest.
- 294a62a84b6b Sunday 17:00: research round, up to three candidates.
- ab11bdfec604 first Sunday 18:00: full retest.

## Open work, in priority order

Per-asset models for ETH and the majors. Cross-sectional alt ranking as long-short deciles. BTC at 1-day and 3-day horizons, reporting which horizon the factors actually price. TA factors as conditioning variables on the forecast. Universe expanded to the top 50 alts by open interest across Binance, Bybit, OKX and Hyperliquid. Intraday series for the short-term layer. See research/backlog.md.

## Broken

Laevitas get_market_positioning_history returns a bare server error. It blocks market-wide OI dominance and the put/call ratio. One attempt per week, no more.
