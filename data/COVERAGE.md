# Liquidation coverage, checked 2026-11-19

liq_BTC over oi_BTC has a yearly median of 0.0017 in 2022, 0.0019 in 2023, 0.0023 in 2024, 0.0013 in 2025 and 0.0029 in 2026. The 2026 rise is real in the file.

The cause is not a code change and not a venue change. The Coinalyze file holds one symbol, BTCUSDT_PERP.A, continuous from 2022-09-09 to 2026-11-18, 1,532 rows. The long share of the total moves between 0.30 and 0.75 across months with no step, so the rise is not a change in which side is counted. The daily totals around the rise drift from 5 million to 69 million and back within two weeks, which is a volatile period, not a coverage break: a coverage change would step once and stay.

What remains open is whether the vendor widened what it counts as a liquidation during 2026. The file cannot show that, because it holds one symbol and no venue field. The F4 results rest on this series and are marked void until that is settled.

Computed by scripts/liq_break.py, scripts/liq_break_month.py, scripts/liq_sides.py, scripts/liq_source.py and scripts/liq_step.py.

Funding units. Dashboard funding columns are percent per 8h, where 0.01 is 1 bp. The Laevitas perp_funding pull is the same scale on daily bars and one hundredth of it on hourly bars: the saved daily median is 0.00704 and the saved hourly median is 0.0000386. scripts/fetch_laevitas.py refuses a daily pull whose median is outside 0.001 to 0.05.
