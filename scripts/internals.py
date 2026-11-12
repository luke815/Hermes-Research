"""Market internals from the point-in-time panel. Breadth, funding, open interest.

Reads data/panel_xs/ and writes the internals key of dashboard/data.json. A name
with no history is absent, not filled. Percentiles are against the trailing year
of the same series.

Usage: python3 scripts/internals.py
"""

import json
import os
from datetime import datetime, timezone

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs")
DATA = os.path.join(ROOT, "dashboard", "data.json")


def load():
    frames = []
    for name in sorted(os.listdir(PANEL)):
        frame = pd.read_csv(os.path.join(PANEL, name), usecols=lambda c: c in
                            ("date", "close", "funding_rate", "oi_usd"))
        if "close" not in frame.columns or frame["close"].notna().sum() < 60:
            continue
        frame["name"] = name.replace(".csv", "")
        frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def pct_of_year(series):
    year = series.dropna().iloc[-252:]
    if year.empty:
        return None
    return float((year <= year.iloc[-1]).mean())


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stacked = load()
    if stacked.empty:
        print("no panel")
        return
    wide = stacked.pivot_table(index="date", columns="name", values="close")
    wide = wide.sort_index()
    above_50 = wide.gt(wide.rolling(50, min_periods=50).mean()).mean(axis=1)
    above_200 = wide.gt(wide.rolling(200, min_periods=200).mean()).mean(axis=1)
    at_high = wide.eq(wide.rolling(30, min_periods=30).max()).mean(axis=1)
    at_low = wide.eq(wide.rolling(30, min_periods=30).min()).mean(axis=1)
    last = wide.index[-1]
    funding = stacked.pivot_table(index="date", columns="name", values="funding_rate")
    oi = stacked.pivot_table(index="date", columns="name", values="oi_usd")
    fund_last = funding.loc[last].dropna() if last in funding.index else pd.Series(dtype=float)
    oi_last = oi.loc[last].dropna() if last in oi.index else pd.Series(dtype=float)
    internals = {
        "as_of": str(last),
        "universe_n": int(wide.loc[last].notna().sum()),
        "breadth": {
            "above_50d": round(float(above_50.loc[last]), 4) if pd.notna(above_50.loc[last]) else None,
            "above_200d": round(float(above_200.loc[last]), 4) if pd.notna(above_200.loc[last]) else None,
            "new_highs_minus_lows": round(float((at_high - at_low).loc[last]), 4),
        },
        "funding": {
            "median": round(float(fund_last.median()), 6) if len(fund_last) else None,
            "share_negative": round(float((fund_last < 0).mean()), 4) if len(fund_last) else None,
        },
        "oi": {"total_usd": round(float(oi_last.sum()), 0) if len(oi_last) else None},
        "pct_1y": {
            "above_50d": pct_of_year(above_50),
            "above_200d": pct_of_year(above_200),
            "new_highs_minus_lows": pct_of_year(at_high - at_low),
        },
        "series": {
            "date": list(wide.index[-252:]),
            "above_50d": [None if pd.isna(v) else round(float(v), 4) for v in above_50.iloc[-252:]],
            "above_200d": [None if pd.isna(v) else round(float(v), 4) for v in above_200.iloc[-252:]],
        },
    }
    data = json.load(open(DATA))
    data["internals"] = internals
    tmp = DATA + ".tmp"
    json.dump(data, open(tmp, "w"))
    os.replace(tmp, DATA)
    print(f"internals as_of {internals['as_of']} names {internals['universe_n']} "
          f"above_50d {internals['breadth']['above_50d']}")


if __name__ == "__main__":
    main()
