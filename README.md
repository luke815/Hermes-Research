# Regime tester

Tests whether Laevitas-style derivatives indicators have predictive power on the
underlying token's own price. Indicators are scored in isolation and in every
combination, always walk-forward (no look-ahead).

## Layout

```
data/inbox/      drop CSV or JSON exports here
data/processed/  aligned panels written by the loader
reports/         one markdown + csv per run
regime_tester/   the code
```

## Drop format

One file per series, or one wide file. The loader finds a timestamp column
(`date`, `timestamp`, `time`, `ts`, ms epoch or ISO) and keeps every numeric
column as an indicator.

Price can live in the same file (`price`, `close`, `index`, `index_price`) or
in its own file. If a file has no price column, its name is treated as the
token (`BTC.csv`, `btc_funding.csv` -> BTC) and it is joined to whichever file
does carry that token's price.

Laevitas API JSON (`{"data": {"items": [...]}}`) is accepted as-is.

Tenor columns named `7`, `30`, `90` are renamed to `<file>_<tenor>` so they
don't collide across files.

## Run

```
python3 -m regime_tester.run --inbox data/inbox --horizon 24
```

Horizon is in bars of the aligned panel (default: hourly, so 24 = 1 day ahead).

## What "predictive power" means here

For each indicator, and each combination of up to 3:

1. Causal features only: level z-score, change, trailing rank. All use a
   trailing window, shifted so bar t never sees bar t.
2. Regimes are trailing quintiles of the feature, fit only on past bars.
Target is the token's return over the `--horizon` bars *after* each bar.
Features are shifted by one, so the signal at bar t uses only data from
before t, and it is scored against the move that follows t.
4. Reported per regime: hit rate vs the base rate, mean forward return, and a
   t-stat on the return difference. Combinations are scored the same way on
   the joint regime, plus an agreement score (how often the legs point the
   same direction, and whether that subset beats either leg alone).

A high score with a tiny sample is noise. The report flags cells under 30
observations.
