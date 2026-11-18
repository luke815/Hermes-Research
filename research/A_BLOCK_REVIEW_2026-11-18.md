# A-block review, 2026-11-18

Received as two parts. The items stay open: A1, A2, A3, A4, A5, A6, L7, L8, L9, L10. L12 closes once the probe script is committed and the 403 note is softened. C9 is re-run. C8 keeps its rejected verdict but the reason is rewritten.

## What is still wrong
- A1 is not blocked. The OKX walk only sums stopped OKX names, and nothing calls funding_sum.write_sum, so Binance, Bybit and live OKX sums are never produced. The remaining parts are in the message: the partial last row, the funding sum daemon, base_of, the descending-file test through the real readers, and a code-written results file that reconciles 842, 156 and 1,897.
- A2 records no cross-sectional verdict. confirm_cell raises on every cross-sectional cell because panel is None, and the daemon restarts batch 1 forever. Score through the sweep's own path, net of 2 times 15 bps, and void on error.
- A3 uses a 1.5 times perturbation, which rv_ratio and atm_inversion ignore because they are scale-free. Use seeded noise. The RAW restore was claimed and not done.
- A4's costs and periods modules were not in git. They are now, in 83a815c. The ranking still does not mask each date to names listed that day, and the cost check was one leg.
- A6's counter is hand-written and the daemon overwrites it. is_neighbour lives in pick_next_cell.py, which is now committed, and confirm_daemon does not use it.
- C9's carry is understated by about 100 times, the ranking filters on the forward return, and there is no pre-registration. Re-run after a pre-registration commit.
- C8 stays rejected. The reason should say validation t 1.01 on 251 dates did not reach 2, and the test is a null, not a flip.

## Also committed
regime_tester/costs.py, periods.py, episodes.py, events.py, scripts/pick_next_cell.py, intraday_store.py, env_token.py, http_get.py. Twelve committed scripts import them and could not be re-run from git until this commit.
