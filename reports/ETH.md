# ETH regime test

Forward return horizon: 5 bars ahead. Features are shifted by one, so a signal never sees the bar it is scored against. Regimes are walk-forward quintiles (0 = lowest trailing, 4 = highest). `thin = yes` means under 30 observations; ignore the t-stat there.

## Isolation

| indicator | transform | regime | n | mean_fwd_return | edge_vs_base | hit_rate | hit_edge | tstat | thin |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| oi_dominance_spread | z | 1 | 196 | -0.0128 | -0.0210 | 0.5102 | -0.0289 | -4.28 |  |
| oi_dominance_spread | z | 0 | 275 | 0.0202 | 0.0119 | 0.6000 | 0.0609 | 2.55 |  |
| funding | rank | 4 | 493 | 0.0209 | 0.0092 | 0.5781 | 0.0333 | 2.34 |  |
| alt_oi_weighted_funding | rank | 4 | 189 | 0.0183 | 0.0100 | 0.5714 | 0.0324 | 2.13 |  |
| funding | rank | 2 | 272 | 0.0011 | -0.0106 | 0.4963 | -0.0484 | -1.93 |  |
| oi_dominance_spread | z | 3 | 182 | 0.0174 | 0.0091 | 0.5604 | 0.0214 | 1.60 |  |
| oi_dominance_spread | z | 2 | 211 | 0.0022 | -0.0061 | 0.4834 | -0.0556 | -1.26 |  |
| alt_oi_weighted_funding | rank | 2 | 204 | 0.0045 | -0.0038 | 0.5392 | 0.0002 | -0.73 |  |
| funding | rank | 1 | 258 | 0.0078 | -0.0039 | 0.5349 | -0.0099 | -0.69 |  |
| alt_oi_weighted_funding | rank | 0 | 231 | 0.0052 | -0.0031 | 0.5281 | -0.0109 | -0.59 |  |
| alt_oi_weighted_funding | rank | 3 | 176 | 0.0051 | -0.0032 | 0.5114 | -0.0277 | -0.57 |  |
| oi_dominance_spread | z | 4 | 173 | 0.0110 | 0.0027 | 0.5202 | -0.0188 | 0.53 |  |
| funding | rank | 0 | 413 | 0.0094 | -0.0023 | 0.5472 | 0.0024 | -0.48 |  |
| funding | rank | 3 | 563 | 0.0123 | 0.0006 | 0.5417 | -0.0030 | 0.15 |  |
| alt_oi_weighted_funding | rank | 1 | 237 | 0.0089 | 0.0006 | 0.5443 | 0.0052 | 0.13 |  |

## Combinations

Agreement: every leg in an extreme quintile and all pointing the same way. Regime +1 / -1 is the agreed direction.

| indicator | kind | regime | n | mean_fwd_return | edge_vs_base | hit_rate | hit_edge | tstat | thin |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| oi_dominance_spread:z + funding:rank + alt_oi_weighted_funding:rank | agreement | 1 | 202 | 0.0201 | 0.0118 | 0.5594 | 0.0204 | 2.30 |  |
| oi_dominance_spread:z + alt_oi_weighted_funding:rank | agreement | 1 | 210 | 0.0196 | 0.0113 | 0.5571 | 0.0181 | 2.22 |  |
| oi_dominance_spread:z + funding:rank | agreement | 1 | 272 | 0.0168 | 0.0085 | 0.5625 | 0.0234 | 1.96 |  |
| funding:rank + alt_oi_weighted_funding:rank | agreement | 1 | 350 | 0.0125 | 0.0043 | 0.5457 | 0.0067 | 1.14 |  |
| oi_dominance_spread:z + funding:rank + alt_oi_weighted_funding:rank | agreement | -1 | 254 | 0.0137 | 0.0055 | 0.5866 | 0.0476 | 1.02 |  |
| oi_dominance_spread:z + funding:rank | agreement | -1 | 271 | 0.0126 | 0.0043 | 0.5830 | 0.0440 | 0.85 |  |
| oi_dominance_spread:z + alt_oi_weighted_funding:rank | agreement | -1 | 321 | 0.0119 | 0.0036 | 0.5794 | 0.0404 | 0.80 |  |
| funding:rank + alt_oi_weighted_funding:rank | agreement | -1 | 338 | 0.0072 | -0.0011 | 0.5473 | 0.0083 | -0.25 |  |
