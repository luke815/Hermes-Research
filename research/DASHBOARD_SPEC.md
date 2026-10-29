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
