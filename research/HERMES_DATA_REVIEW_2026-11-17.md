# Hermes data and edge review, 2026-11-17

This comes from a 7-agent review: a pipeline audit, a live probe of the Laevitas API, a map of data against research coverage, and web research on data with evidence of an edge. A second agent checked each of the first two reports and dropped any claim it could refute. The put/call ratio and butterfly results were re-checked by hand.

## Laevitas: working or not

**Verdict: partly working.** The daily BTC and ETH series that the dashboard and research use are current through 2026-11-16. On that date they match Laevitas exactly: BTC 7-day skew 18.26, 7-day ATM IV 48.03, 30-day risk reversal −7.46, and OI-weighted funding 0.00203. The large per-instrument download works, but it is slow and has code flaws that will stop it updating. Three series Hermes records as "unavailable" are actually served.

| Dataset | Status | Last date | Note |
|---|---|---|---|
| DVOL BTC/ETH | Working | 2026-11-16 | 7 missing days, including 2026-10-21 |
| ATM IV by tenor | BTC working, ETH short | 2026-11-16 | ETH daily data only starts 2025-10-21, so there is no ETH training period |
| 25d skew | Working, with holes | 2026-11-16 | 16 missing days, including 10-21 and 11-02 |
| 25d risk reversal | Working, with holes | 2026-11-16 | Missing 10-21, 11-02, 11-11 and 11-12. Laevitas has 11-11 and 11-12 today |
| 90d basis | Working | 2026-11-16 | 22 old gaps, none recent |
| OI-weighted funding | Working | 2026-11-16 | Matches the vendor |
| Realized vol | BTC working, ETH partial | 2026-11-16 | ETH daily data starts 2024-10-01. For 2024-10 to 2025-10, hourly rows overwrite the daily ones in derivatives.py |
| Perpetuals (5,185 instruments) | Pulled, but will stop updating | 2026-11-16 | 129 files are empty. NADO (73) and BULLISH (37) return HTTP 400 and are never retried |
| Dated futures (171) | Pulled, unused | 2026-11-17 | Live contracts only. No code reads them |
| Option contract list | Done | 2026-11-17 | 16,602 contracts across 240 maturities. Paradex, derive, gate and bullish are skipped. Aevo is still listed but has been dead since 2024-06-11 |
| Option contract histories | In progress | 1,040 of 16,602 at 09:10Z | About 94 hours left at 2.8 per minute. No code reads them |
| Liquidations by currency | Not started (queued on purpose) | — | 11,061 rows, about 61 hours, waiting behind options |
| Realtime snapshots | Unknown | First set 2026-11-16 | 52 files. Whether the 11-17 run happened can't be seen from the repo |
| Put/call OI ratio, futures OI total | Not held, but served | Vendor has them to 2026-11-17 | Hermes logs a "server error" |
| 25d butterfly | Not held, but served | Vendor has 2019-03-31 to 2026-11-17 (2,764 rows) | Hermes logs "not served" |
| v2 REST (inbox exports, hourly windows) | Blocked by 403 on Hermes's machine | 2025-10-20 / 2025-10-01 | Cause unknown |

**What is wrong, all checked by a second reviewer:**
- **The daily series have no proper script.** They are pulled each day by an AI job using the Laevitas connector, not by a script, so a failed day stays a permanent hole.
- **The dashboard date can hide a stale series.** It shows the newest date of any series, so a risk reversal that is 3 days old still looks fresh. The data-health panel lists only Coinalyze.
- **The per-instrument puller will stop updating.**
  - Any file it fully downloaded counts as complete forever, so it is never extended. After 14 days those coins drift into "delisted".
  - One instrument that keeps failing stalls the whole queue.
  - A 400 or 404 error is treated as done forever, so those instruments are never retried.
  - It is possible, but not confirmed, that about 5,000 older perpetual files reopen at 2026-11-18 00:00Z and stall the options download again.
- **The download order is backwards for research.** Option contracts, which are live contracts only and have little history, run before liquidations, which go back to 2021-11-20.

**Hermes's three recurring errors:**
- **No wrong URL path was found.** The v2 scripts use the documented host and /api/v1 paths.
- **v2 returns 403: cause unknown.** The missing User-Agent theory was tested and did not reproduce: from the reviewer's machine a default Python request got 402, not 403. Two causes remain possible and are unconfirmed: the key may not be entitled to v2 REST, or Hermes's machine may be IP-blocked. It costs little either way, because most v2 history only starts 2025-09 or later.
- **"Positioning history returns 500": it works now.** The put/call ratio and futures OI total both returned data through the connector.
- **Bare "server error" on skew and risk reversal.** Leaving out `type=25d` reproduces exactly that bare 400. Also:
  - Requests with date-only timestamps were rejected.
  - Windows longer than a year return 503.
  - Hermes did succeed on many days, so it is not confirmed that a missing parameter caused its intermittent failures.

All of these checks ran from the review session through its own Laevitas connector, not from Hermes's machine or with its key.

## Data Hermes holds but is not using for edge

**Short answer: no, it is not using what it has.** The L6 research item has sat at the top of the queue for 5 runs, blocked on a download it does not need. Recent effort went to 8 single-asset BTC/ETH event tests that could never pass: the bar is 30 episodes and BTC has only 14 tops and 22 bottoms in total.

Ranked by likely value:
1. **The Laevitas per-coin panel (data/panel_xs_laevitas).** It holds funding, open interest, basis and long/short ratio for 5,056 instruments from 2021-03-26.
   - Only the training-period sweep uses it.
   - Its 30 confirmation checks on 2026-11-17 were scored on the wrong panel and the wrong measure (confirm.py:159-169). All 30 show the same validation t of −0.2472 on 549 points. This is the known audit bug C2, still running.
   - Its best leads (long/short ratio, training t of −4.29 and −4.05) have never been tested on held-out data.
2. **BTC/ETH market-level options and derivatives series, 2021 to 2026-11-16.**
   - They have never been tested on their own at 1-3 days. Earlier rejections only judged them as add-ons to the heat score.
   - The S8 sweep listed 1,296,000 options test cells and 1,036,800 derivatives cells, and scored none.
   - The coin-margined vs stablecoin-margined funding gap and the implied-minus-realized vol (ivrv_btc) files have never been used.
3. **Data on delisted coins, needed for a survivor-free universe.**
   - Bybit prices for stopped coins: 308 names, 173,595 days, and no code reads them.
   - Binance long/short ratio for stopped coins is never joined into the panel.
4. **Coinalyze liquidations: 30,325 rows from 2022-07/09.** A cascade definition was never set in advance, although the cascade measure already exists in indicators.py.
5. **Funding and basis compared across venues for the same coin.** There are up to 25 instruments per coin, plus 350 Hyperliquid perpetuals. This can be built but never has been. The evidence for it is weak, so it would only serve as a filter.
6. **Market breadth across the 1,611-coin panel.** It appears on the dashboard only and has never been scored beyond 16 names.
7. **Low value for now:**
   - The 171 dated futures, the 1,040+ option contract histories and the realtime snapshots: live contracts only, or too little history.
   - Fear and Greed.
   - The hourly files from 2024-10 to 2025-10.

## The research plan Hermes should run with what it already has

**First, A1-A4 exactly as the audit wrote them.** Three additions:
- **A2** voids the 30 confirmations from 2026-11-17 and fixes confirm.py. Pause the confirmation job until then.
- **A4** builds the survivor-free universe from the span files plus the Bybit stopped-coin prices and the Laevitas panel.
- **A6:** stop the BTC/ETH single-asset event tests now.

Then, ranked:
1. **A7(1): 1-3 day reversal with a liquidity/open-interest floor, on the survivor-free panel.**
   - Data: panel_xs, panel_xs_laevitas and the Bybit stopped-coin prices. The $20M open-interest floor needs the Laevitas open interest, because panel_xs has it for only 29 stopped names.
   - Horizon: 1-3 days.
   - Why: it is Hermes's only lead that kept its sign in all three periods. It is fading, though: the correlation went from −0.032 to −0.016 to −0.010, and the test-period t is −1.16. Published work says this effect lives in illiquid coins, so the floor and trading costs will decide it.
2. **A7(2): the derivatives family for BTC/ETH, and as a filter on test 1.**
   - Data: on disk now: DVOL, ATM IV term structure, risk reversal, basis, OI-weighted funding, the funding gap, and DVOL minus realized vol. Butterfly and put/call join once they are pulled.
   - Skew and risk reversal are one signal: skew equals risk reversal divided by ATM IV, sign flipped, which matched on three days checked. Count them once in A2.
   - Horizon: 1-6 days.
   - Why: it is the audit's second-best candidate. One 2026 dissertation finds BTC risk reversal predicts over days 1-6, which is thin evidence. It has never been tested on its own. Run it BTC-only until the ETH history is backfilled.
3. **Laevitas per-coin positioning on held-out data:** the long/short ratio leads, the funding rank with carry charged (A7(4)), and pooled open-interest crowding before altcoin tops (A7(3)).
   - Data: panel_xs_laevitas.
   - Horizon: 1-7 days.
   - Why: these are Hermes's strongest training-period results and have never been checked properly. Published work shows funding carry has shrunk since 2024, so carry must be charged.
4. **Momentum across coins over 2-4 weeks, on the survivor-free panel.**
   - Horizon: 1-4 weeks, weekly rebalance.
   - Why: it is the strongest factor in the published work (Liu, Tsyvinski and Wu 2022; Borri et al. find +2.1% a week after 2020). Some papers find it dead after mid-2020. Hermes's earlier rejection used a universe of surviving coins only.
5. **Liquidation cascade, then 1-5 day reversal.**
   - Data: Coinalyze liquidations now, Laevitas liquidations later.
   - Why: audit lead #5, and a definition was never set in advance.
6. **Risk dial R1, with basis as a crash-risk signal.**
   - Data: trend, realized vol, DVOL, funding, basis, open interest, liquidations and breadth. Almost all of it is on disk.
   - Horizon: 1-4 weeks.
   - Why: BIS working paper 1087 links high carry to later crashes. R1 is marked blocked, but its inputs are mostly already held.

## Data worth adding

**Does Hermes need more data? A little.** Most of what it needs comes through the Laevitas subscription you already have, and Hermes can pull it itself. Only rows 6, 7, 9 and 10 need you.

| # | Data | Why | Provider | Cost | Who acts |
|---|---|---|---|---|---|
| 1 | Put/call OI ratio (from 2020-09-25), options OI, futures OI total | Feeds C5, R1 and open-interest change on down days, all currently marked absent | Laevitas | $0 (already paid) | Hermes pulls |
| 2 | 25d butterfly from 2019-03-31. DVOL, ATM IV, skew and risk reversal for 2019-03-31 to 2020-12-31. ETH daily ATM IV and realized vol as far back as served | About 21 more months for BTC, and a training period for ETH. How far back ETH goes was not checked | Laevitas | $0 | Hermes |
| 3 | Basis curve across 7 tenors (from 2021-03-26, treat zeros as missing). BTC/ETH perpetual open interest, liquidations and volume (from 2021-03-26) | Carry and crash-risk regime. Open-interest change on down days | Laevitas | $0 | Hermes |
| 4 | Per-coin history for about 494 delisted coins (LUNA, FTT and SRM are served) | A survivor-free universe with funding, open interest and basis, for A4 | Laevitas | $0 | Hermes |
| 5 | Liquidation history: BTC/ETH aggregated from 2021-11-20, in windows of a year or less; then per coin | Cascade test and R1 | Laevitas | $0 | Hermes (reorder the puller) |
| 6 | Market cap and circulating supply | Size and turnover factors. Hermes has none | CoinGecko | Free demo key (rate-limited); paid tiers for full history | You (get a key) |
| 7 | Token unlock schedules | The only scheduled, altcoin-specific 1-4 week signal found, useful for the short side. Evidence is from a practitioner study of 40 tokens | Tokenomist (DefiLlama has a subset free) | About $69-99/month (Pro) or $250/month (API) | You (buy) |
| 8 | Stablecoin supply | Liquidity regime over 5-20 days. Evidence is mixed | DefiLlama | Free, no key | Hermes |
| 9 | Macro: DXY, US 10-year, NDX | Risk-dial context, not price direction | FRED, stooq | Free | You (FRED key); Hermes (stooq) |
| 10 | Spot ETF flows | Weak: flows mostly follow price | SoSoValue, Farside, Coinglass | Free key, or $29/month | You (key). Low priority |

**Not worth adding now:**
- CryptoQuant exchange netflows: about $99/month, and the evidence is intraday only.
- Order-book data.
- History from Hyperliquid wallets, dealer gamma (GEX) and the fitted vol surface: reported to start 2025-08 or 2026-06 with method breaks. This was not re-checked.
- Fixing the v2 403: it mainly unlocks histories that start 2025-09 or later.

## Message for Hermes

Telegram limits a message to 4,096 characters, so this is in two parts.

```
PART 1/2. Outside review of Laevitas data and research use, 2026-11-17. A1-A4 still come first. The probes below ran from an outside session, not your box or key: re-check from the box.

CORRECT YOUR RECORDS
1. Put/call OI, futures OI total and 25d butterfly are served. get_market_positioning_history series=options_oi_pc_ratio deribit BTC 1d returned rows 2026-11-10..17 (history from 2020-09-25). futures_oi_total BTC returned rows to 2026-11-17. get_options_volatility_history series=butterfly type=25d returned 2,764 rows from 2019-03-31. Remove the "server error, one attempt per week" rule (MANDATE.md:35, backlog.md:183) and "no butterfly is served" (regime_tester/derivatives.py:11-12).
2. Call format: type=25d is required for skew, risk_reversal and butterfly. No type, or type=25, gives a bare 400 invalid_request. Use full ISO timestamps (2026-11-10T00:00:00Z). Request history in windows of 1 year or less; multi-year windows gave 503 source_unavailable.
3. No wrong URL path found: fetch_laevitas.py and fetch_window.py use the documented apiv2 host and /api/v1 paths. The 403 cause is unknown.
4. L6 is not blocked. Per-name funding_rate and oi_usd are in data/panel_xs_laevitas (5,056 files from 2021-03-26). C5 and R1 inputs are market-level and on disk to 2026-11-16.
5. Skew 25d = risk reversal / ATM IV x 100, sign flipped (matched 11-14..11-16). Count them as one family in A2.
6. The 30 confirmations of 2026-11-17 (all val t -0.2472, n=549) were scored by confirm.py:159-169 on data/panel_xs with 14d momentum, not on the cells. Void them under A2; pause the confirm daemon until A2 lands. Apply A6 now: BTC has 14 tops and 22 bottoms against a 30-episode bar.

NEW BACKLOG ITEMS
- L7. Puller freshness and queue. In scripts/laevitas_pull.py, a file is complete only if its last bar >= the closed day, fully paged or not. A 500 or timeout moves the row to the back instead of retrying left[0]. A 400/404 is retried after 7 days (NADO 73, BULLISH 37). Done when tests show a fully paged file from yesterday is pending today, one failing name does not stall the next, and the perpetual store's newest bar advances daily.
- L8. Pull order. Liquidations by currency for BTC, ETH and names passing the X1 floor run before option-contract histories. Pull BTC/ETH aggregated liquidations from 2021-11-20 now via get_derivatives_liquidation_history in yearly windows. Done when BTC/ETH liquidation history from 2021-11-20 is on disk.
- L9. Market-level backfill: options_oi_pc_ratio (BTC, ETH); futures_oi_total; butterfly 25d; oi_weighted_basis (7 tenors from 2021-03-26, 0 = missing); derivatives_summary BTC/ETH (perp OI, liquidations, volume from 2021-03-26); DVOL/ATM IV/skew/RR for 2019-03-31..2020-12-31; ETH daily ATM IV and RV as far back as served; holes: RR 2026-11-11 and 11-12, all options series 2026-10-21, skew/RR 2026-11-02. Done when each series has first date, last date and missing-day count in data/INVENTORY.md.
```

```
PART 2/2.
- L10. Deterministic daily Laevitas refresh. Replace the LLM regime-daily-refresh with a script on the v1 routes in data/laevitas/INVENTORY.md:35-44. Each run re-requests the last 14 days and fills gaps. Also:
  - the derivatives key shows each series' own last date, not max();
  - data_health lists Laevitas rows;
  - derivatives.py skips the hourly *_p*/*_t* files in the daily merge;
  - build_universe_laevitas runs after the puller;
  - the scheduler catches up a missed slot and keeps its own results file.
  Done when a deleted day is refilled on the next run with no model action, and a stale RR shows as stale on the dashboard.
- L11. Delisted names. Pull Laevitas per-symbol history for the ~494 delisted names in the Binance/Bybit/OKX span files (LUNA, FTT, SRM are served). Merge with panel_xs_laevitas and data/bybit_prices (308 names). Done when A4's universe has funding, OI and basis for dead names from 2021.
- L12. v2 403 test. From the box, one GET to apiv2.laevitas.ch/api/v1/derivatives/funding-history with the .env key in X-API-Key, once with the default User-Agent and once with Mozilla/5.0. Never print or log the key. Done when both status codes and response bodies are logged. If both are 403, tell the user to ask Laevitas whether the key covers v2 REST. Low priority: most v2 history starts 2025-09 or later.
- C8. Liquidation cascade. Pre-register a cascade definition on Coinalyze liquidations (on disk from 2022-07), then test 1-5 day forward returns for BTC and pooled, three periods, HAC errors. Done when scored.
- C9. Cross-sectional momentum, 2-4 week lookback, weekly rebalance, per-leg costs, on the A4 survivor-free panel. Done when scored across three periods.

ORDER AFTER A1-A4
1) A7(1) reversal with OI floor on the merged panel.
2) A7(2) derivatives family, BTC/ETH at 1-6 days and as a filter on 1). Add butterfly, P/C, basis curve and funding_dispersion_oiw. BTC-only until ETH is backfilled.
3) A7(3), A7(4), and the Laevitas long/short leads (train t -4.29, -4.05) out of sample after A2.
4) C9. 5) C8. 6) R1.
Every A7 item must name the panel it uses.

REPORT BACK
- L7 test results, and the perpetual store's newest bar on 2026-11-19.
- Each L9 series: first date, last date, rows, missing days.
- L12 status codes.
- Options and liquidation ETA after L8.
- Why 15,742 option contracts are "remaining" when 16,602 - 1,040 = 15,562.
- A2: number of voided confirmations, and the re-scored top 5 Laevitas cells.
- Anything that needs a paid key or purchase (CoinGecko, Tokenomist, FRED), so the user can decide.
```