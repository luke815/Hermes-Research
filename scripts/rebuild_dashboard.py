"""Rebuild panel, heat score, rolling two-year pricing model, dashboard JSON."""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/opt/data/workspace/regime-tester")
sys.path.insert(0, str(ROOT))

from regime_tester.factors import build_factors
from regime_tester.heat import COMPONENTS, heat_score
from regime_tester.panel import OUT, build

HORIZON = 10
WINDOW = 730
MIN_FIT = 400
BAND = 0.4


def clean_overlap() -> None:
    """basis_*_d starts on the date already stored in the prior window."""
    raw = ROOT / "data" / "raw"
    for stem in ("basis_btc_d", "basis_eth_d"):
        path = raw / f"{stem}.json"
        rows = json.loads(path.read_text())
        kept = [r for r in rows if r["date"] > 1761004800000]
        if len(kept) != len(rows):
            path.write_text(json.dumps(kept))
            print(f"trimmed {stem}: {len(rows)} -> {len(kept)}")


def rolling_pricing(scored: pd.DataFrame, factors: pd.DataFrame) -> dict:
    names = [c for c in COMPONENTS if c in factors.columns]
    x = factors[names]
    fwd = scored["btc_price"].shift(-HORIZON) / scored["btc_price"] - 1
    predicted = pd.Series(index=scored.index, dtype=float)
    weights = None
    for i, ts in enumerate(scored.index):
        if i < WINDOW:
            continue
        train_x = x.iloc[i - WINDOW:i]
        train_y = fwd.iloc[i - WINDOW:i]
        both = pd.concat([train_x, train_y.rename("y")], axis=1).dropna()
        if len(both) < MIN_FIT:
            continue
        matrix = np.column_stack([np.ones(len(both)), both[names].to_numpy()])
        coef, *_ = np.linalg.lstsq(matrix, both["y"].to_numpy(), rcond=None)
        row = x.loc[ts, names]
        if row.isna().any():
            continue
        predicted.loc[ts] = coef[0] + float(np.dot(coef[1:], row.to_numpy()))
        weights = coef
    last = x.iloc[-1]
    intercept = float(weights[0])
    slope_map = {name: float(weights[i + 1]) for i, name in enumerate(names)}
    # dashboard forecast is a line in heat: fit expected return on heat over the
    # same trailing window, so the readout matches the learned model at the
    # current heat level
    heat = scored["heat"]
    tail = pd.concat([heat.rename("h"), fwd.rename("y")], axis=1).dropna().iloc[-WINDOW:]
    h = np.column_stack([np.ones(len(tail)), tail["h"].to_numpy()])
    line, *_ = np.linalg.lstsq(h, tail["y"].to_numpy(), rcond=None)
    return {
        "predicted": predicted,
        "learned": [{"name": n, "weight": round(slope_map[n], 4)} for n in names],
        "forecast": {
            "intercept": round(float(line[0]), 5),
            "slope": round(float(line[1]), 5),
            "note": "Expected BTC return over the next 10 days. Reliable only when heat is elevated; the cold end has not held up out of sample.",
        },
        "rank": ranking(predicted, fwd),
    }


def ranking(predicted: pd.Series, fwd: pd.Series) -> str:
    both = pd.concat([predicted.rename("p"), fwd.rename("y")], axis=1).dropna()
    if len(both) < 50:
        return "too few"
    top = both[both["p"] >= both["p"].quantile(0.8)]["y"].mean()
    bot = both[both["p"] <= both["p"].quantile(0.2)]["y"].mean()
    return f"top fifth {top:+.1%}, bottom fifth {bot:+.1%}, n={len(both)}"


def crossings(heat: pd.Series, price: pd.Series, level: float, down: bool) -> list:
    prior = heat.shift(1)
    mask = (prior >= level) & (heat < level) if down else (prior < level) & (heat >= level)
    points = []
    for ts in heat.index[mask.fillna(False)]:
        px = price.loc[ts]
        if pd.notna(px):
            points.append({"t": ts.strftime("%Y-%m-%d"), "p": round(float(px), 2)})
    return points


def main() -> None:
    clean_overlap()
    panel = build()
    # score only days where price and basis both exist; today's price bar is
    # still forming and basis has not printed for it yet
    complete = panel["btc_price"].notna() & panel["basis_btc"].notna() & panel["eth_funding"].notna()
    panel = panel.loc[: complete[complete].index[-1]]
    panel.to_csv(OUT)
    print(f"panel {len(panel)} rows, last {panel.index[-1].date()}")

    scored = heat_score(panel)
    factors = build_factors(panel)
    model = rolling_pricing(scored, factors)

    valid = scored.dropna(subset=["heat", "btc_price"])
    dates = [ts.strftime("%Y-%m-%d") for ts in valid.index]
    legs = {}
    for name in COMPONENTS:
        column = f"leg_{name}"
        legs[name] = [None if pd.isna(v) else round(float(v), 4) for v in valid[column]]

    predicted = model["predicted"].reindex(valid.index)
    payload = {
        "dates": dates,
        "price": [round(float(v), 2) for v in valid["btc_price"]],
        "heat": [round(float(v), 4) for v in valid["heat"]],
        "hot": crossings(valid["heat"], valid["btc_price"], BAND, down=False),
        "cold": crossings(valid["heat"], valid["btc_price"], -BAND, down=True),
        "components": [
            {"name": name, "weight": 1, "direction": direction}
            for name, direction in COMPONENTS.items()
        ],
        "legs": legs,
        "forecast": model["forecast"],
        "predicted": [None if pd.isna(v) else round(float(v), 5) for v in predicted],
        "learned_weights": model["learned"],
        "forecast_model": "rolling 2-year regression, refit daily",
    }
    out = ROOT / "reports" / "heat_data.json"
    out.write_text(json.dumps(payload))
    last = valid.index[-1]
    print(f"heat {valid['heat'].iloc[-1]:+.3f} on {last.date()}")
    print(f"forecast line {model['forecast']}")
    print(f"learned {model['learned']}")
    print(f"ranking {model['rank']}")
    print(f"predicted last {predicted.iloc[-1]}")
    print(f"wrote {out} bytes {out.stat().st_size}")
    # readings the ledger needs
    fwd = panel["btc_price"].shift(-HORIZON) / panel["btc_price"] - 1
    print("ledger_heat", round(float(valid["heat"].iloc[-1]), 4))
    print("ledger_forecast", None if pd.isna(predicted.iloc[-1]) else round(float(predicted.iloc[-1]), 5))
    print("ledger_price", round(float(valid["btc_price"].iloc[-1]), 2))
    ten_back = last - pd.Timedelta(days=HORIZON)
    if ten_back in predicted.index and pd.notna(predicted.loc[ten_back]) and pd.notna(fwd.loc[ten_back]):
        print("prior_date", ten_back.date(), "prior_forecast", round(float(predicted.loc[ten_back]), 5),
              "realized", round(float(fwd.loc[ten_back]), 5))


if __name__ == "__main__":
    main()
