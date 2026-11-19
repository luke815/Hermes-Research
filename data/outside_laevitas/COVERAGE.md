# Laevitas CSV coverage

Generated 2026-11-18 14:22 UTC from `/private/tmp/claude-501/-Users-biggucci-Library-Application-Support-Claude-scratch-workspaces-0ce23b70-34e4-4508-8903-f93599b339fb-7453e5ce-def2-496e-a6ed-b03b1c832b47-scratch-2026-11-17-da2bed/3dba4e51-4497-4a26-8449-ca1c3f49915f/scratchpad/research/data/laevitas`. 40 CSV files scanned (recursive). CSVs were read only, not modified.

Definitions: **rows** excludes the header; **null share** = null cells / (rows x columns) over all columns including `date`; **longest gap** = largest difference between consecutive timestamps after sorting and de-duplicating; **gaps > step** = number of consecutive-timestamp gaps larger than the nominal cadence (1h / 1d), with the total number of missing periods implied; **expected rows** = periods between first and last timestamp at nominal cadence. Cadence is taken from the `_1d` / `_1h` filename suffix. Thresholds: < 300 rows (daily) or < 5,000 rows (hourly) are flagged.

## Flags

- `price_BTC_coinbase_1h.csv`: only 4250 rows (< 5000 hourly threshold)
- `price_ETH_coinbase_1h.csv`: only 4258 rows (< 5000 hourly threshold)

## Notes (not flags)

- Latest timestamp across all files: 2026-11-18 13:00 UTC.
- Series ending more than 30 days before that (stale for recent-period analysis):
  - `pos_options_oi_BTC_1d.csv` ends 2024-12-31 (687 days behind).
  - `pos_options_oi_ETH_1d.csv` ends 2024-12-31 (687 days behind).
  - `pos_pcratio_BTC_1d.csv` ends 2025-03-31 (597 days behind).
  - `pos_pcratio_ETH_1d.csv` ends 2025-06-30 (506 days behind).
  - `price_BTC_coinbase_1h.csv` ends 2025-04-29 23:00 (567 days behind).
  - `price_ETH_coinbase_1h.csv` ends 2025-04-29 23:00 (567 days behind).
- Files missing more than 1% of nominal periods between first and last timestamp:
  - `price_BTC_1h.csv`: 1,131 of 17,942 periods missing (6.3%), spread over 633 gaps.
  - `price_BTC_coinbase_1h.csv`: 70 of 4,320 periods missing (1.6%), spread over 6 gaps.
  - `price_ETH_1h.csv`: 1,135 of 17,942 periods missing (6.3%), spread over 639 gaps.
  - `price_ETH_coinbase_1h.csv`: 62 of 4,320 periods missing (1.4%), spread over 7 gaps.
- Columns with >= 10% nulls, with the span over which the column is populated:
  - `options_atmiv_BTC_1d.csv` `1`: 22.5% null; first valid 2020-09-25, last valid 2026-11-18.
  - `options_atmiv_BTC_1d.csv` `270`: 19.4% null; first valid 2020-09-25, last valid 2026-11-18.
  - `options_atmiv_BTC_1d.csv` `365`: 13.8% null; first valid 2019-03-31, last valid 2026-11-18.
  - `options_atmiv_ETH_1d.csv` `1`: 22.3% null; first valid 2020-09-25, last valid 2026-11-18.
  - `options_atmiv_ETH_1d.csv` `270`: 19.4% null; first valid 2020-09-25, last valid 2026-11-18.
  - `options_atmiv_ETH_1d.csv` `365`: 15.5% null; first valid 2019-10-25, last valid 2026-11-18.
  - `options_bf25_BTC_1d.csv` `1`: 22.6% null; first valid 2020-09-25, last valid 2026-11-18.
  - `options_bf25_BTC_1d.csv` `270`: 19.4% null; first valid 2020-09-25, last valid 2026-11-18.
  - `options_bf25_BTC_1d.csv` `365`: 14.0% null; first valid 2019-03-31, last valid 2026-11-18.
  - `options_bf25_ETH_1d.csv` `1`: 22.0% null; first valid 2020-09-25, last valid 2026-11-18.
  - `options_bf25_ETH_1d.csv` `270`: 19.4% null; first valid 2020-09-25, last valid 2026-11-18.
  - `options_bf25_ETH_1d.csv` `365`: 15.2% null; first valid 2019-10-25, last valid 2026-11-18.
  - `options_rr25_BTC_1d.csv` `1`: 22.6% null; first valid 2020-09-25, last valid 2026-11-18.
  - `options_rr25_BTC_1d.csv` `270`: 19.4% null; first valid 2020-09-25, last valid 2026-11-18.
  - `options_rr25_BTC_1d.csv` `365`: 13.6% null; first valid 2019-03-31, last valid 2026-11-18.
  - `options_rr25_ETH_1d.csv` `1`: 22.0% null; first valid 2020-09-25, last valid 2026-11-18.
  - `options_rr25_ETH_1d.csv` `270`: 19.4% null; first valid 2020-09-25, last valid 2026-11-18.
  - `options_rr25_ETH_1d.csv` `365`: 15.2% null; first valid 2019-10-25, last valid 2026-11-18.
  - `options_skew25_BTC_1d.csv` `1`: 22.3% null; first valid 2020-09-25, last valid 2026-11-18.
  - `options_skew25_BTC_1d.csv` `270`: 19.4% null; first valid 2020-09-25, last valid 2026-11-18.
  - `options_skew25_BTC_1d.csv` `365`: 13.6% null; first valid 2019-03-31, last valid 2026-11-18.
  - `options_skew25_ETH_1d.csv` `1`: 22.3% null; first valid 2020-09-25, last valid 2026-11-18.
  - `options_skew25_ETH_1d.csv` `270`: 19.4% null; first valid 2020-09-25, last valid 2026-11-18.
  - `options_skew25_ETH_1d.csv` `365`: 15.5% null; first valid 2019-10-25, last valid 2026-11-18.
  - `perp_oi_BTC_1d.csv` `oi_coin`: 62.1% null; first valid 2024-09-24, last valid 2026-11-18.
  - `perp_oi_ETH_1d.csv` `oi_coin`: 62.1% null; first valid 2024-09-24, last valid 2026-11-18.
- Longest-gap windows shared by 3+ files (likely upstream outages rather than per-file issues):
  - 2021-03-13 00:00 -> 2021-03-18 00:00 (5d): 12 files.
  - 2021-06-02 00:00 -> 2021-06-05 00:00 (3d): 6 files.
  - 2026-07-26 06:00 -> 2026-07-27 08:00 (1d 2h): 4 files.
  - 2026-01-30 06:00 -> 2026-01-30 08:00 (2h): 4 files.

## Per-file summary

| File | Cadence | First | Last | Rows | Expected rows | Cols | Null share | Longest gap | Gap window | Gaps > step (missing periods) | Flags |
|---|---|---|---|---:|---:|---:|---:|---|---|---|---|
| `options_atmiv_BTC_1d.csv` | daily | 2019-03-31 | 2026-11-18 | 2,766 | 2,790 | 10 | 7.47% | 5d | 2021-03-13 00:00 -> 2021-03-18 00:00 | 15 (24) | OK |
| `options_atmiv_BTC_1h.csv` | hourly | 2024-11-01 00:00 | 2026-11-18 13:00 | 17,923 | 17,942 | 10 | 0.09% | 7h | 2026-10-20 19:00 -> 2026-10-21 02:00 | 13 (19) | OK |
| `options_atmiv_ETH_1d.csv` | daily | 2019-03-31 | 2026-11-18 | 2,766 | 2,790 | 10 | 7.61% | 5d | 2021-03-13 00:00 -> 2021-03-18 00:00 | 15 (24) | OK |
| `options_atmiv_ETH_1h.csv` | hourly | 2024-11-01 00:00 | 2026-11-18 13:00 | 17,922 | 17,942 | 10 | 0.09% | 7h | 2026-10-20 19:00 -> 2026-10-21 02:00 | 14 (20) | OK |
| `options_bf25_BTC_1d.csv` | daily | 2019-03-31 | 2026-11-18 | 2,765 | 2,790 | 10 | 7.61% | 5d | 2021-03-13 00:00 -> 2021-03-18 00:00 | 16 (25) | OK |
| `options_bf25_ETH_1d.csv` | daily | 2019-03-31 | 2026-11-18 | 2,765 | 2,790 | 10 | 7.35% | 5d | 2021-03-13 00:00 -> 2021-03-18 00:00 | 16 (25) | OK |
| `options_dvol_BTC_1d.csv` | daily | 2021-03-25 | 2026-11-18 | 2,058 | 2,065 | 3 | 0.00% | 3d | 2022-06-01 00:00 -> 2022-06-04 00:00 | 6 (7) | OK |
| `options_dvol_BTC_1h.csv` | hourly | 2024-11-01 00:00 | 2026-11-18 13:00 | 17,833 | 17,942 | 2 | 0.00% | 18h | 2026-07-26 06:00 -> 2026-07-27 00:00 | 66 (109) | OK |
| `options_dvol_ETH_1d.csv` | daily | 2021-03-25 | 2026-11-18 | 2,058 | 2,065 | 3 | 0.00% | 3d | 2022-06-01 00:00 -> 2022-06-04 00:00 | 6 (7) | OK |
| `options_dvol_ETH_1h.csv` | hourly | 2024-11-01 00:00 | 2026-11-18 13:00 | 17,833 | 17,942 | 2 | 0.00% | 18h | 2026-07-26 06:00 -> 2026-07-27 00:00 | 66 (109) | OK |
| `options_ivrv_BTC_1d.csv` | daily | 2019-03-30 | 2026-11-18 | 2,766 | 2,791 | 13 | 0.00% | 4d | 2021-02-16 00:00 -> 2021-02-20 00:00 | 22 (25) | OK |
| `options_ivrv_ETH_1d.csv` | daily | 2019-03-30 | 2026-11-18 | 2,766 | 2,791 | 13 | 0.00% | 4d | 2021-02-16 00:00 -> 2021-02-20 00:00 | 22 (25) | OK |
| `options_rr25_BTC_1d.csv` | daily | 2019-03-31 | 2026-11-18 | 2,765 | 2,790 | 10 | 7.49% | 5d | 2021-03-13 00:00 -> 2021-03-18 00:00 | 16 (25) | OK |
| `options_rr25_BTC_1h.csv` | hourly | 2024-11-01 00:00 | 2026-11-18 13:00 | 17,866 | 17,942 | 10 | 0.09% | 1d 2h | 2026-07-26 06:00 -> 2026-07-27 08:00 | 32 (76) | OK |
| `options_rr25_ETH_1d.csv` | daily | 2019-03-31 | 2026-11-18 | 2,765 | 2,790 | 10 | 7.35% | 5d | 2021-03-13 00:00 -> 2021-03-18 00:00 | 16 (25) | OK |
| `options_rr25_ETH_1h.csv` | hourly | 2024-11-01 00:00 | 2026-11-18 13:00 | 17,866 | 17,942 | 10 | 0.09% | 1d 2h | 2026-07-26 06:00 -> 2026-07-27 08:00 | 32 (76) | OK |
| `options_skew25_BTC_1d.csv` | daily | 2019-03-31 | 2026-11-18 | 2,765 | 2,790 | 10 | 7.35% | 5d | 2021-03-13 00:00 -> 2021-03-18 00:00 | 16 (25) | OK |
| `options_skew25_BTC_1h.csv` | hourly | 2024-11-01 00:00 | 2026-11-18 13:00 | 17,865 | 17,942 | 10 | 0.09% | 1d 2h | 2026-07-26 06:00 -> 2026-07-27 08:00 | 33 (77) | OK |
| `options_skew25_ETH_1d.csv` | daily | 2019-03-31 | 2026-11-18 | 2,765 | 2,790 | 10 | 7.58% | 5d | 2021-03-13 00:00 -> 2021-03-18 00:00 | 16 (25) | OK |
| `options_skew25_ETH_1h.csv` | hourly | 2024-11-01 00:00 | 2026-11-18 13:00 | 17,866 | 17,942 | 10 | 0.09% | 1d 2h | 2026-07-26 06:00 -> 2026-07-27 08:00 | 32 (76) | OK |
| `perp_funding_BTC_1d.csv` | daily | 2021-03-26 | 2026-11-18 | 2,055 | 2,064 | 3 | 0.02% | 3d | 2021-06-02 00:00 -> 2021-06-05 00:00 | 7 (9) | OK |
| `perp_funding_BTC_1h.csv` | hourly | 2025-09-28 08:00 | 2026-11-18 13:00 | 9,989 | 9,990 | 5 | 0.08% | 2h | 2026-01-30 06:00 -> 2026-01-30 08:00 | 1 (1) | OK |
| `perp_funding_ETH_1d.csv` | daily | 2021-03-26 | 2026-11-18 | 2,055 | 2,064 | 3 | 0.02% | 3d | 2021-06-02 00:00 -> 2021-06-05 00:00 | 7 (9) | OK |
| `perp_funding_ETH_1h.csv` | hourly | 2025-09-28 08:00 | 2026-11-18 13:00 | 9,989 | 9,990 | 5 | 0.08% | 2h | 2026-01-30 06:00 -> 2026-01-30 08:00 | 1 (1) | OK |
| `perp_oi_BTC_1d.csv` | daily | 2021-03-26 | 2026-11-18 | 2,054 | 2,064 | 5 | 12.41% | 3d | 2021-06-02 00:00 -> 2021-06-05 00:00 | 8 (10) | OK |
| `perp_oi_BTC_1h.csv` | hourly | 2025-09-28 08:00 | 2026-11-18 13:00 | 9,989 | 9,990 | 5 | 0.00% | 2h | 2026-01-30 06:00 -> 2026-01-30 08:00 | 1 (1) | OK |
| `perp_oi_ETH_1d.csv` | daily | 2021-03-26 | 2026-11-18 | 2,054 | 2,064 | 5 | 12.41% | 3d | 2021-06-02 00:00 -> 2021-06-05 00:00 | 8 (10) | OK |
| `perp_oi_ETH_1h.csv` | hourly | 2025-09-28 08:00 | 2026-11-18 13:00 | 9,989 | 9,990 | 5 | 0.00% | 2h | 2026-01-30 06:00 -> 2026-01-30 08:00 | 1 (1) | OK |
| `pos_futures_oi_BTC_1d.csv` | daily | 2021-03-26 | 2026-11-18 | 2,056 | 2,064 | 7 | 0.00% | 3d | 2021-06-02 00:00 -> 2021-06-05 00:00 | 6 (8) | OK |
| `pos_futures_oi_ETH_1d.csv` | daily | 2021-03-26 | 2026-11-18 | 2,056 | 2,064 | 7 | 0.00% | 3d | 2021-06-02 00:00 -> 2021-06-05 00:00 | 6 (8) | OK |
| `pos_options_oi_BTC_1d.csv` | daily | 2020-09-25 | 2024-12-31 | 1,546 | 1,559 | 4 | 0.03% | 5d | 2021-03-13 00:00 -> 2021-03-18 00:00 | 7 (13) | OK |
| `pos_options_oi_ETH_1d.csv` | daily | 2020-09-25 | 2024-12-31 | 1,546 | 1,559 | 4 | 0.92% | 5d | 2021-03-13 00:00 -> 2021-03-18 00:00 | 7 (13) | OK |
| `pos_pcratio_BTC_1d.csv` | daily | 2020-09-25 | 2025-03-31 | 1,636 | 1,649 | 6 | 0.00% | 5d | 2021-03-13 00:00 -> 2021-03-18 00:00 | 7 (13) | OK |
| `pos_pcratio_ETH_1d.csv` | daily | 2020-09-25 | 2025-06-30 | 1,726 | 1,740 | 6 | 0.00% | 5d | 2021-03-13 00:00 -> 2021-03-18 00:00 | 8 (14) | OK |
| `price_BTC_1h.csv` | hourly | 2024-11-01 00:00 | 2026-11-18 13:00 | 16,811 | 17,942 | 6 | 0.00% | 1d 20h | 2024-11-20 09:00 -> 2024-11-22 05:00 | 633 (1,131) | OK |
| `price_BTC_1h_filled.csv` | hourly | 2024-11-01 00:00 | 2026-11-18 13:00 | 17,880 | 17,942 | 7 | 0.00% | 1d 1h | 2025-07-05 23:00 -> 2025-07-07 00:00 | 6 (62) | OK |
| `price_BTC_coinbase_1h.csv` | hourly | 2024-11-01 00:00 | 2025-04-29 23:00 | 4,250 | 4,320 | 6 | 0.00% | 23h | 2024-11-17 07:00 -> 2024-11-18 06:00 | 6 (70) | only 4250 rows (< 5000 hourly threshold) |
| `price_ETH_1h.csv` | hourly | 2024-11-01 00:00 | 2026-11-18 13:00 | 16,807 | 17,942 | 6 | 0.00% | 1d 20h | 2024-11-20 09:00 -> 2024-11-22 05:00 | 639 (1,135) | OK |
| `price_ETH_1h_filled.csv` | hourly | 2024-11-01 00:00 | 2026-11-18 13:00 | 17,883 | 17,942 | 7 | 0.00% | 1d 1h | 2025-07-05 23:00 -> 2025-07-07 00:00 | 6 (59) | OK |
| `price_ETH_coinbase_1h.csv` | hourly | 2024-11-01 00:00 | 2025-04-29 23:00 | 4,258 | 4,320 | 6 | 0.00% | 19h | 2024-11-17 12:00 -> 2024-11-18 07:00 | 7 (62) | only 4258 rows (< 5000 hourly threshold) |

## Columns and per-column null share

Only columns with at least one null are listed under nulls.

### `options_atmiv_BTC_1d.csv`

- Columns (10): `date`, `1`, `7`, `14`, `30`, `60`, `90`, `180`, `270`, `365`
- Nulls: `1` 22.5%, `270` 19.4%, `365` 13.8%, `7` 3.2%, `14` 3.2%, `30` 3.2%, `60` 3.2%, `90` 3.2%, `180` 3.2%

### `options_atmiv_BTC_1h.csv`

- Columns (10): `date`, `1`, `7`, `14`, `30`, `60`, `90`, `180`, `270`, `365`
- Nulls: `1` 0.1%, `7` 0.1%, `14` 0.1%, `30` 0.1%, `60` 0.1%, `90` 0.1%, `180` 0.1%, `365` 0.1%, `270` 0.1%

### `options_atmiv_ETH_1d.csv`

- Columns (10): `date`, `1`, `7`, `14`, `30`, `60`, `90`, `180`, `270`, `365`
- Nulls: `1` 22.3%, `270` 19.4%, `365` 15.5%, `180` 3.7%, `7` 3.0%, `14` 3.0%, `30` 3.0%, `60` 3.0%, `90` 3.0%

### `options_atmiv_ETH_1h.csv`

- Columns (10): `date`, `1`, `7`, `14`, `30`, `60`, `90`, `180`, `270`, `365`
- Nulls: `1` 0.1%, `7` 0.1%, `14` 0.1%, `30` 0.1%, `60` 0.1%, `90` 0.1%, `180` 0.1%, `365` 0.1%, `270` 0.1%

### `options_bf25_BTC_1d.csv`

- Columns (10): `date`, `1`, `7`, `14`, `30`, `60`, `90`, `180`, `270`, `365`
- Nulls: `1` 22.6%, `270` 19.4%, `365` 14.0%, `30` 3.4%, `60` 3.4%, `90` 3.4%, `180` 3.4%, `7` 3.3%, `14` 3.3%

### `options_bf25_ETH_1d.csv`

- Columns (10): `date`, `1`, `7`, `14`, `30`, `60`, `90`, `180`, `270`, `365`
- Nulls: `1` 22.0%, `270` 19.4%, `365` 15.2%, `180` 3.4%, `7` 2.7%, `14` 2.7%, `30` 2.7%, `60` 2.7%, `90` 2.6%

### `options_dvol_BTC_1d.csv`

- Columns (3): `date`, `dvol`, `index`
- Nulls: none

### `options_dvol_BTC_1h.csv`

- Columns (2): `date`, `value`
- Nulls: none

### `options_dvol_ETH_1d.csv`

- Columns (3): `date`, `dvol`, `index`
- Nulls: none

### `options_dvol_ETH_1h.csv`

- Columns (2): `date`, `value`
- Nulls: none

### `options_ivrv_BTC_1d.csv`

- Columns (13): `date`, `iv_7`, `iv_30`, `iv_60`, `iv_90`, `iv_180`, `iv_365`, `rv_7`, `rv_30`, `rv_60`, `rv_90`, `rv_180`, `rv_365`
- Nulls: none

### `options_ivrv_ETH_1d.csv`

- Columns (13): `date`, `iv_7`, `iv_30`, `iv_60`, `iv_90`, `iv_180`, `iv_365`, `rv_7`, `rv_30`, `rv_60`, `rv_90`, `rv_180`, `rv_365`
- Nulls: none

### `options_rr25_BTC_1d.csv`

- Columns (10): `date`, `1`, `7`, `14`, `30`, `60`, `90`, `180`, `270`, `365`
- Nulls: `1` 22.6%, `270` 19.4%, `365` 13.6%, `30` 3.4%, `7` 3.3%, `14` 3.3%, `60` 3.1%, `90` 3.0%, `180` 3.0%

### `options_rr25_BTC_1h.csv`

- Columns (10): `date`, `1`, `7`, `14`, `30`, `60`, `90`, `180`, `270`, `365`
- Nulls: `1` 0.1%, `365` 0.1%, `7` 0.1%, `14` 0.1%, `30` 0.1%, `60` 0.1%, `90` 0.1%, `180` 0.1%, `270` 0.1%

### `options_rr25_ETH_1d.csv`

- Columns (10): `date`, `1`, `7`, `14`, `30`, `60`, `90`, `180`, `270`, `365`
- Nulls: `1` 22.0%, `270` 19.4%, `365` 15.2%, `180` 3.4%, `7` 2.7%, `14` 2.7%, `30` 2.7%, `60` 2.7%, `90` 2.6%

### `options_rr25_ETH_1h.csv`

- Columns (10): `date`, `1`, `7`, `14`, `30`, `60`, `90`, `180`, `270`, `365`
- Nulls: `1` 0.1%, `7` 0.1%, `14` 0.1%, `30` 0.1%, `60` 0.1%, `90` 0.1%, `180` 0.1%, `365` 0.1%, `270` 0.1%

### `options_skew25_BTC_1d.csv`

- Columns (10): `date`, `1`, `7`, `14`, `30`, `60`, `90`, `180`, `270`, `365`
- Nulls: `1` 22.3%, `270` 19.4%, `365` 13.6%, `30` 3.0%, `60` 3.0%, `90` 3.0%, `180` 3.0%, `7` 3.0%, `14` 3.0%

### `options_skew25_BTC_1h.csv`

- Columns (10): `date`, `1`, `7`, `14`, `30`, `60`, `90`, `180`, `270`, `365`
- Nulls: `1` 0.1%, `7` 0.1%, `14` 0.1%, `30` 0.1%, `60` 0.1%, `90` 0.1%, `180` 0.1%, `365` 0.1%, `270` 0.1%

### `options_skew25_ETH_1d.csv`

- Columns (10): `date`, `1`, `7`, `14`, `30`, `60`, `90`, `180`, `270`, `365`
- Nulls: `1` 22.3%, `270` 19.4%, `365` 15.5%, `180` 3.7%, `7` 3.0%, `14` 3.0%, `30` 3.0%, `60` 3.0%, `90` 2.9%

### `options_skew25_ETH_1h.csv`

- Columns (10): `date`, `1`, `7`, `14`, `30`, `60`, `90`, `180`, `270`, `365`
- Nulls: `1` 0.1%, `7` 0.1%, `14` 0.1%, `30` 0.1%, `60` 0.1%, `90` 0.1%, `180` 0.1%, `365` 0.1%, `270` 0.1%

### `perp_funding_BTC_1d.csv`

- Columns (3): `date`, `value`, `funding_coinm`
- Nulls: `value` 0.0%

### `perp_funding_BTC_1h.csv`

- Columns (5): `date`, `value`, `funding_rate_close`, `basis_close`, `annualized_carry`
- Nulls: `value` 0.1%, `funding_rate_close` 0.1%, `annualized_carry` 0.1%

### `perp_funding_ETH_1d.csv`

- Columns (3): `date`, `value`, `funding_coinm`
- Nulls: `value` 0.0%

### `perp_funding_ETH_1h.csv`

- Columns (5): `date`, `value`, `funding_rate_close`, `basis_close`, `annualized_carry`
- Nulls: `value` 0.1%, `funding_rate_close` 0.1%, `annualized_carry` 0.1%

### `perp_oi_BTC_1d.csv`

- Columns (5): `date`, `value`, `oi_coin`, `price`, `volume_usd`
- Nulls: `oi_coin` 62.1%

### `perp_oi_BTC_1h.csv`

- Columns (5): `date`, `value`, `oi_open`, `oi_high`, `oi_low`
- Nulls: none

### `perp_oi_ETH_1d.csv`

- Columns (5): `date`, `value`, `oi_coin`, `price`, `volume_usd`
- Nulls: `oi_coin` 62.1%

### `perp_oi_ETH_1h.csv`

- Columns (5): `date`, `value`, `oi_open`, `oi_high`, `oi_low`
- Nulls: none

### `pos_futures_oi_BTC_1d.csv`

- Columns (7): `date`, `value`, `f_u`, `f_c`, `p_u`, `p_c`, `value_coin`
- Nulls: none

### `pos_futures_oi_ETH_1d.csv`

- Columns (7): `date`, `value`, `f_u`, `f_c`, `p_u`, `p_c`, `value_coin`
- Nulls: none

### `pos_options_oi_BTC_1d.csv`

- Columns (4): `date`, `value`, `notional_usd`, `premium_usd`
- Nulls: `premium_usd` 0.1%

### `pos_options_oi_ETH_1d.csv`

- Columns (4): `date`, `value`, `notional_usd`, `premium_usd`
- Nulls: `premium_usd` 3.7%

### `pos_pcratio_BTC_1d.csv`

- Columns (6): `date`, `p`, `c`, `pc`, `p_notional`, `c_notional`
- Nulls: none

### `pos_pcratio_ETH_1d.csv`

- Columns (6): `date`, `p`, `c`, `pc`, `p_notional`, `c_notional`
- Nulls: none

### `price_BTC_1h.csv`

- Columns (6): `date`, `open`, `high`, `low`, `close`, `volume`
- Nulls: none

### `price_BTC_1h_filled.csv`

- Columns (7): `date`, `open`, `high`, `low`, `close`, `volume`, `source`
- Nulls: none

### `price_BTC_coinbase_1h.csv`

- Columns (6): `date`, `open`, `high`, `low`, `close`, `volume`
- Nulls: none

### `price_ETH_1h.csv`

- Columns (6): `date`, `open`, `high`, `low`, `close`, `volume`
- Nulls: none

### `price_ETH_1h_filled.csv`

- Columns (7): `date`, `open`, `high`, `low`, `close`, `volume`, `source`
- Nulls: none

### `price_ETH_coinbase_1h.csv`

- Columns (6): `date`, `open`, `high`, `low`, `close`, `volume`
- Nulls: none
