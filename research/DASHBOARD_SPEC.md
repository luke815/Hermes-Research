# Dashboard: how to feed and host it

The dashboard is one file, `dashboard/index.html`. Do not edit it. It reads one file next to it, `dashboard/data.json`, and renders everything from that. Your only job is to write `data.json` after every refresh and to keep the folder hosted at a stable address. If `data.json` is missing or malformed the page shows clearly labelled sample data, so a broken write is visible immediately.

## Who writes it
Only `regime-daily-refresh` writes `data.json`, as its last step, after the panel passes `verify_panel.py`. The hourly job may update only `setups`, `jobs` and `generated_at` by reading the file, changing those keys, and writing it back. Write to `data.json.tmp` and rename, never in place.

## Units
- Dates: ISO `YYYY-MM-DD`. Timestamps: ISO 8601 UTC.
- Returns and spreads: percent as plain numbers (`2.66` means +2.66%). Never fractions.
- Factor values, heat, learned weights: plain numbers. Weights: fractions summing to 1 across active factors.
- Funding: as the source reports it. Prices: USD.
- Series arrays are aligned to `series.date` and the same length. Use `null` for a missing value, never skip an index.
- `series` carries every column of the panel, not just the ones the main charts use: price, funding, open interest, liquidations and long/short per asset, basis, OI-weighted funding, realized vol, DVOL, skew, ATM IV and risk reversal for BTC and ETH, heat, forecast and every factor. Name per-asset columns `<measure>_<SYMBOL>` (`funding_SOL`, `oi_SOL`). The explore pane lists every key it finds, so anything left out is invisible. Expect the file to be around 1 to 2 MB; that is fine.

## Contract
```json
{
  "generated_at": "2026-10-28T05:31:04Z",
  "panel_end": "2026-10-27",
  "regime": {
    "score": -0.11, "hot": 0.4, "cold": -0.4,
    "label": "Momentum and volatility, four factors",
    "change_7d": -0.04,
    "note": "Hot zone above +0.4 has held out of sample. Cold zone and middle carry no reliable edge."
  },
  "forecast": { "btc_10d": -0.03, "reliable": false, "zone_hit_rate": null, "zone_n": null },
  "series": {
    "date": ["2020-01-01", "..."],
    "btc": [7200.1, "..."],
    "eth": [130.2, "..."],
    "heat": [0.12, "..."],
    "forecast_btc_10d": [1.4, "..."],
    "factors": { "btc_ret_30": [0.3, "..."], "btc_vol_z90": ["..."], "btc_trend_stretch": ["..."], "eth_funding_z30": ["..."] }
  },
  "factors": [
    { "name": "btc_ret_30", "label": "BTC 30-day momentum", "measures": "How hard price has already been running",
      "weight": 0.25, "learned": 0.143, "value": -0.57,
      "oos_btc": 3.68, "oos_alt": 8.39, "n": 236, "sign_holds": true, "status": "active" },
    { "name": "basis_gap_btc_eth", "label": "BTC vs ETH basis gap", "measures": "BTC basis relative to ETH basis",
      "weight": 0, "learned": null, "value": null, "oos_btc": -0.51, "oos_alt": 0.07, "n": 197, "sign_holds": false, "status": "dropped" }
  ],
  "alt_ranking": [
    { "rank": 1, "symbol": "SOL", "score": 1.21, "expected_10d": 4.2, "rs_30": 6.1, "funding_7d": 0.0081, "oi_change_7d": 12.4, "price": 148.2 }
  ],
  "alt_ranking_note": "Optional one-line description shown under the heading",
  "setups": [
    { "tier": "A", "asset": "SOL", "direction": "long", "horizon": "10d", "expected": 4.2, "hit_rate": 0.61, "n": 88,
      "trigger": "Heat +0.52, Donchian 20-day breakout with volume confirmation.", "invalidation": "Close below 141.0", "opened": "2026-10-28" }
  ],
  "setups_note": "Optional sentence shown when setups is empty",
  "ledger": { "rows": [ { "date": "2026-10-16", "heat": 0.05, "forecast": 2.1, "realized": -1.8, "hit": false } ] },
  "data_health": [
    { "series": "BTC, ETH spot price", "source": "Coinalyze", "venue": "Binance", "last": "2026-10-27", "rows": 2492, "status": "ok", "note": "" }
  ],
  "research": [
    { "date": "2026-10-27", "decision": "dropped", "what": "basis_btc_z30, basis_gap_btc_eth, dispersion_14 removed from the score",
      "why": "Sign flips on the full history. Four-factor model out of sample: BTC +2.66%, alts +6.43%." }
  ],
  "jobs": [
    { "name": "regime-daily-refresh", "last_run": "2026-10-28T05:31Z", "status": "OK",
      "line": "STATUS OK regime-daily-refresh panel_end=2026-10-27 age=1d files=results/2026-10-28_refresh.json" }
  ]
}
```

Allowed values: `factors[].status` is `active`, `watch` or `dropped`. `data_health[].status` is `ok`, `lag` or `stale`. `research[].decision` is `added`, `dropped`, `rejected`, `changed` or `retested`. `setups[].tier` is `A`, `B` or `C`. `ledger.rows[].realized` and `hit` are `null` until the horizon has passed.

Every key except `generated_at`, `panel_end`, `regime`, `series.date`, `series.btc` and `series.heat` is optional; the page shows an empty state for what is missing. Never invent a value to fill a section. An empty `alt_ranking` with no model is correct; a fabricated one is a FAIL.

The `research` array is the last 30 entries of `research/log.md`, newest first. The `ledger.rows` array is the full `signals/ledger.csv`.

Every row in `factors` carries `oos_btc`, `oos_alt`, `n` and `sign_holds` from the latest results file, for active and dropped factors alike. A factor row with those fields empty while a results file holds them is a FAIL.

## Research program keys (page version 2)
The page renders four more keys, all optional, all with empty states. Write them as soon as the underlying work exists and never before.

```json
{
  "ideas": [
    { "symbol": "SOL", "side": "long", "setup": "compression breakout", "horizon": "10d", "tier": "A",
      "rank": 3, "decile": 1, "expected": 4.2, "hit_rate": 0.61, "n": 88,
      "drivers": [ { "name": "bb_width_pct", "value": 0.09 }, { "name": "oi_change_1d", "value": 6.4 }, { "name": "funding_pct", "value": 0.41 } ],
      "invalidation": "close below 141.0", "gate": "heat +0.46, open", "venue": "Binance", "size_hint": "0.6 units", "opened": "2026-11-03" }
  ],
  "ideas_note": "Optional sentence shown when both lists are empty",
  "watchlist": [
    { "symbol": "LINK", "side": "short", "setup": "crowded long", "distance": "funding at 86th percentile, needs 90th for 3 days", "date": "2026-11-03" }
  ],
  "setup_library": [
    { "name": "crowded long", "side": "short", "horizon": "10d", "status": "admitted",
      "triggers": 212, "triggers_by_year": { "2021": 41, "2022": 30, "2023": 28, "2024": 52, "2025": 39, "2026": 22 },
      "hit_rate": 0.58, "mean_net": 2.1, "baseline": 0.3, "ci": [0.9, 3.4],
      "by_tercile": { "cold": 1.2, "mid": 1.9, "hot": 3.0 },
      "live_n": 4, "live_hit_rate": 0.5, "last_retest": "2026-11-02" }
  ],
  "ranking_stats": {
    "by_year": [ { "year": "2024", "ic_mean": 0.041, "ic_t": 3.2, "decile_spread": 3.1, "turnover": 0.35, "n": 366 } ],
    "by_tercile": [ { "tercile": "hot", "ic_mean": 0.062, "ic_t": 2.8, "decile_spread": 4.4, "turnover": 0.33, "n": 410 } ],
    "note": "Optional one line on the composite's current definition"
  }
}
```

`relative_strength` is the intraday board, written by the hourly job (it may write this key alongside setups, jobs and generated_at; it still never writes the panel). It replaces the `relative`, `relative_intraday` and `leaders` keys, which are retired.

```json
"relative_strength": {
  "as_of": "2026-11-03T12:00:00Z",
  "universe": "Top 100 by open interest across Binance, Bybit and OKX, hourly bars.",
  "windows": ["1h", "4h", "24h", "7d", "30d", "90d"],
  "benchmarks": { "BTC": { "1h": 0.1, "4h": 0.4, "24h": -1.2, "7d": -5.4, "30d": -8.1, "90d": 18.8 }, "ETH": { }, "SOL": { } },
  "rows": [
    { "symbol": "ARB", "ret": { "1h": 2.0, "4h": 3.8, "24h": 4.1, "7d": 9.0, "30d": 12.5, "90d": 93.7 },
      "vs_btc": { "1h": 1.9, "4h": 3.4 }, "vs_eth": { }, "vs_sol": { },
      "oi_usd": 120000000, "funding": 0.0081 }
  ]
}
```

Rules: returns are percent over the window, computed from the last completed bar (never a partial bar); `vs_*` is the name's return minus the benchmark's return over the same window; every window in `windows` is present for every row or null; BTC, ETH and SOL appear as rows too, so they can be read against each other. The universe is the top 100 by open interest at the time of the write, refreshed hourly from a 1-hour pull of the last 100 bars for those names (batches of 20 symbols per Coinalyze call). The 7d, 30d and 90d windows come from the daily panel. If the pull fails, write the previous board with its old `as_of` rather than zeros.

`book` is the long/short book; its shape is defined in LONG_SHORT_BOOK.md section 10 and the page renders every field there, with empty states for anything missing. Status is `provisional` until the strategy backtester admits the rule.

The page also polls `live.json` from the `live` branch every 60 seconds; its contract and the daemon that writes it are in LIVE_LAYER.md. Keys present in live.json (relative_strength, watchlist, ideas, book_live) take precedence over the daily copies on the page.

## Daily output keys (page version 3)
Four keys written every morning by scheduler jobs, from the full point-in-time panel, in code. They are data and provisional scores, labelled as such on the page; they do not wait for an admitted signal.

```json
"internals": {
  "as_of": "2026-11-12", "universe_n": 312,
  "breadth": { "above_20d": 0.34, "above_50d": 0.21, "above_200d": 0.08, "new_highs_minus_lows": -0.08 },
  "funding": { "median": 0.0041, "share_crowded": 0.07, "share_negative": 0.22 },
  "oi": { "total_usd": 48300000000, "change_1d": -0.6, "change_7d": -3.1, "share_at_90d_high": 0.04 },
  "liquidations": { "long_usd": 212000000, "short_usd": 96000000 },
  "pct_1y": { "above_50d": 0.31, "above_200d": 0.22, "new_highs_minus_lows": 0.35, "liquidations": 0.62 },
  "series": { "date": [], "above_50d": [], "above_200d": [], "median_funding": [], "total_oi": [] }
},
"cycle": {
  "as_of": "2026-11-12",
  "btc": { "candidate_top": false, "candidate_bottom": true, "dist_60d_high": -19.2, "dist_60d_low": 1.8,
           "base_top_30d": 0.21, "n_top_episodes": 61, "base_bottom_30d": 0.18, "n_bottom_episodes": 72 },
  "universe": { "share_at_60d_high": 0.03, "share_at_60d_low": 0.41, "base_top_30d": 0.19, "base_bottom_30d": 0.24,
                "n_top_episodes": 77, "n_bottom_episodes": 97 },
  "note": "one sentence on definitions and status"
},
"universe_rank": {
  "as_of": "2026-11-12", "note": "Equal weights until the sweep confirms components.",
  "rows": [ { "symbol": "SOL", "exchange": "binance", "sector": "L1", "score": 0.91, "decile": 1, "rs_14": 6.1, "rs_30": 12.4,
              "oi_change_7d": 4.6, "funding_pct": 0.42, "vol_trend": 1.35, "range_pos": 0.64, "oi_usd": 870000000,
              "long_ok": true, "short_ok": false, "reasons": "" } ]
},
"sweep": {
  "as_of": "2026-11-12T06:00:00Z", "cells_enumerated": 440440, "cells_tested": 61240, "cells_per_hour": 2100,
  "eligible": 14210, "fragile": 30100, "duplicates": 16930, "insufficient": 6,
  "by_family": [ { "family": "momentum", "tested": 9000, "survivors": 40, "threshold_now": 3.05 } ],
  "leaderboard": [ { "family": "momentum", "cell_id": "rs_30|xs_rank|above|90|rel_10|pit_cross_section|none|daily", "rule": "rs_30 xs_rank above 90",
                     "target": "rel_10", "universe": "pit_cross_section", "train_score": 4.1, "train_n": 410, "status": "unconfirmed" } ],
  "confirmations": [ { "date": "2026-11-12", "cell_id": "...", "validation_t": 0.9, "bar": 3.1, "n": 210, "verdict": "rejected" } ]
}
```

Rules: `internals` covers every name in the point-in-time universe that meets the liquidity rule that day; `pct_1y` is each headline reading's percentile within its own trailing year; `cycle` candidate days and base rates come from the episode counter on the amended targets, BTC alone and the pooled universe, with episodes counted once per date cluster; `universe_rank` is every scored name, not just the legs, with `reasons` naming the first rule a name fails; `sweep.leaderboard` is the top 20 per family and `confirmations` the last 30. Shares and hit rates are fractions, returns percent, as elsewhere. Written by code under the scheduler; the model never writes them.

`backlog` is the research queue, every item in order:

```json
"backlog": [
  { "id": "2", "title": "Costs table and net-return plumbing", "status": "running", "verdict": "", "date": "", "results": "" },
  { "id": "C1", "title": "Targets and episode counter", "status": "queued" },
  { "id": "1", "title": "Point-in-time universe", "status": "insufficient", "verdict": "No source pairs a membership rule with a name list before 2022-09-19; revised rule adopted", "date": "2026-10-30", "results": "results/2026-10-30_pit_universe.json" }
]
```

`backlog[].status` is `queued`, `running`, `admitted`, `rejected`, `insufficient` or `done` (for infrastructure items). Rewrite the key from research/backlog.md on every data.json write.

`setup_library[].status` is `admitted`, `watch`, `rejected` or `insufficient`. `ideas[].side` and `watchlist[].side` are `long` or `short`. Returns are percent as plain numbers, hit rates are fractions. `ideas` replaces `setups` for new work; keep writing `setups` only while the old scanner exists.

## Hosting
The quick tunnel dies on every restart and the address changes. Move the folder to a static host and keep the tunnel only as a fallback.

Preferred: a GitHub repository with Pages enabled on the `main` branch, `dashboard/` folder. After each write of `data.json`, commit and push that one file. Pages serves it within a minute. Needs a token with contents write scope in `.env` as `GITHUB_TOKEN`, and the repository name in `.env` as `DASHBOARD_REPO`. If the repository is private, Pages requires a paid GitHub plan; otherwise use a public repository and keep in mind the data is then public.

If the data must stay gated, use Cloudflare Pages (direct upload via `wrangler pages deploy dashboard/`) with Cloudflare Access in front of the project, which adds an email login. Needs `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` in `.env`.

Whichever host is used, the daily digest prints the dashboard address in its last line, and the hourly job checks the address returns HTTP 200 and that `data.json` at that address has today's or yesterday's `panel_end`.

## Checks before posting the address
1. `data.json` parses and `series.date` has the same length as every other series array.
2. `panel_end` equals the last entry of `series.date`.
3. `verify_panel.py` passed on the panel the file was built from.
4. The hosted `data.json` matches the local one (compare `generated_at`).
