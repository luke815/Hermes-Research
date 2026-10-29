# BTC regime test

Forward return horizon: 5 bars ahead. Features are shifted by one, so a signal never sees the bar it is scored against. Regimes are walk-forward quintiles (0 = lowest trailing, 4 = highest). `thin = yes` means under 30 observations; ignore the t-stat there.

## Isolation

| indicator | transform | regime | n | mean_fwd_return | edge_vs_base | hit_rate | hit_edge | tstat | thin |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| oi_dominance_spread | z | 1 | 196 | -0.0066 | -0.0170 | 0.4898 | -0.0579 | -4.77 |  |
| oi_dominance_spread | z | 3 | 182 | 0.0222 | 0.0117 | 0.5879 | 0.0402 | 2.70 |  |
| oi_dominance_spread | z | 0 | 275 | 0.0179 | 0.0075 | 0.5927 | 0.0450 | 2.06 |  |
| alt_oi_weighted_funding | rank | 4 | 189 | 0.0172 | 0.0068 | 0.6032 | 0.0554 | 1.76 |  |
| funding | z | 3 | 438 | 0.0037 | -0.0052 | 0.5046 | -0.0387 | -1.72 |  |
| oi_dominance_spread | z | 4 | 173 | 0.0070 | -0.0034 | 0.5491 | 0.0014 | -1.14 |  |
| funding | z | 4 | 571 | 0.0124 | 0.0035 | 0.5377 | -0.0056 | 1.13 |  |
| funding | z | 1 | 387 | 0.0120 | 0.0031 | 0.5607 | 0.0175 | 0.90 |  |
| alt_oi_weighted_funding | rank | 3 | 176 | 0.0074 | -0.0030 | 0.5000 | -0.0477 | -0.72 |  |
| funding | z | 0 | 420 | 0.0074 | -0.0015 | 0.5571 | 0.0139 | -0.43 |  |
| funding | z | 2 | 183 | 0.0070 | -0.0019 | 0.5847 | 0.0414 | -0.42 |  |
| alt_oi_weighted_funding | rank | 0 | 231 | 0.0090 | -0.0015 | 0.5671 | 0.0194 | -0.40 |  |
| alt_oi_weighted_funding | rank | 2 | 204 | 0.0088 | -0.0016 | 0.5245 | -0.0232 | -0.39 |  |
| oi_dominance_spread | z | 2 | 211 | 0.0092 | -0.0013 | 0.5071 | -0.0406 | -0.31 |  |
| alt_oi_weighted_funding | rank | 1 | 237 | 0.0100 | -0.0004 | 0.5401 | -0.0076 | -0.11 |  |

## Combinations

Agreement: every leg in an extreme quintile and all pointing the same way. Regime +1 / -1 is the agreed direction.

| indicator | kind | regime | n | mean_fwd_return | edge_vs_base | hit_rate | hit_edge | tstat | thin |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| oi_dominance_spread:z + alt_oi_weighted_funding:rank | agreement | 1 | 210 | 0.0172 | 0.0067 | 0.5952 | 0.0475 | 1.84 |  |
| oi_dominance_spread:z + alt_oi_weighted_funding:rank + funding:z | agreement | 1 | 190 | 0.0155 | 0.0051 | 0.5737 | 0.0260 | 1.36 |  |
| oi_dominance_spread:z + funding:z | agreement | 1 | 281 | 0.0142 | 0.0037 | 0.5587 | 0.0110 | 1.22 |  |
| oi_dominance_spread:z + alt_oi_weighted_funding:rank + funding:z | agreement | -1 | 246 | 0.0133 | 0.0029 | 0.5976 | 0.0498 | 0.79 |  |
| alt_oi_weighted_funding:rank + funding:z | agreement | 1 | 323 | 0.0123 | 0.0019 | 0.5511 | 0.0033 | 0.62 |  |
| oi_dominance_spread:z + alt_oi_weighted_funding:rank | agreement | -1 | 321 | 0.0122 | 0.0017 | 0.5857 | 0.0379 | 0.54 |  |
| alt_oi_weighted_funding:rank + funding:z | agreement | -1 | 323 | 0.0094 | -0.0011 | 0.5573 | 0.0095 | -0.35 |  |
| oi_dominance_spread:z + funding:z | agreement | -1 | 282 | 0.0102 | -0.0002 | 0.5780 | 0.0303 | -0.07 |  |
