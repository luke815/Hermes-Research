"""The ten extremes lists, from the Laevitas panel, one row per coin.

Each list is the top ten names meeting the liquidity floor, ranked by the
measure the setup library already uses, so the page and the research share one
definition. The floor is the book's: 20 million dollars of open interest and
15 million of daily volume, on the last closed day. One row per base coin,
from the venue with the most open interest that day, so a coin listed on three
venues appears once.

The measures, and where they come from:

- crowded_longs: funding at or above its trailing one-year 90th percentile.
- crowded_shorts: funding at or below its trailing one-year 10th percentile.
- volume_surges: volume at least 1.5 times its 20-day median.
- oi_builds: the largest 7-day open-interest rises.
- oi_flushes: the largest 7-day open-interest falls.
- stretched_up: the largest close over the 50-day average, in that average's units.
- stretched_down: the largest close under the 50-day average.
- new_highs: a close at or above the prior 20-day high.
- new_lows: a close at or below the prior 20-day low.
- squeezes: funding at or below its 10th percentile with open interest at a 60-day high.

A list with fewer than ten names is written short rather than padded. Writes
only dashboard/keys/extremes.json. The assembler merges and pushes.
"""

import os
import sys
from glob import glob

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.panel_integrity import base_of  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs_laevitas")
OUT = os.path.join(ROOT, "dashboard", "keys", "extremes.json")
OI_FLOOR = 20_000_000
VOLUME_FLOOR = 15_000_000
LISTS = ("crowded_longs", "crowded_shorts", "volume_surges", "oi_builds", "oi_flushes",
         "stretched_up", "stretched_down", "new_highs", "new_lows", "squeezes")
TOP = 10


def _pct(window, value):
    """Share of the trailing window at or below value. Empty window is absent."""
    if window is None or len(window) == 0 or value is None or pd.isna(value):
        return None
    return float((window <= value).mean())


def readings(frame, day):
    """One name's readings on one day, from bars up to and including that day.

    The percentile windows end the day before, so the day being ranked is not
    inside its own distribution. A window shorter than its lookback is absent.
    """
    history = frame[frame["date"] <= day].sort_values("date")
    if history.empty or history["date"].iloc[-1] != day:
        return None
    last = history.iloc[-1]
    prior = history.iloc[:-1]
    close = last.get("close")
    if pd.isna(close):
        return None
    funding = prior["funding_rate"].tail(365).dropna() if "funding_rate" in prior else pd.Series(dtype=float)
    funding_pct = _pct(funding, last.get("funding_rate")) if len(funding) >= 30 else None
    volume = prior["volume_usd"].tail(20).dropna() if "volume_usd" in prior else pd.Series(dtype=float)
    volume_ratio = (float(last["volume_usd"]) / float(volume.median())
                    if len(volume) >= 20 and volume.median() else None)
    oi = history["oi_usd"].dropna() if "oi_usd" in history else pd.Series(dtype=float)
    oi_change = None
    if len(oi) >= 8:
        earlier = float(oi.iloc[-8])
        oi_change = (float(oi.iloc[-1]) / earlier - 1) if earlier else None
    oi_high = bool(len(oi) >= 60 and float(oi.iloc[-1]) >= float(oi.tail(60).max()))
    average = prior["close"].tail(50).mean() if len(prior) >= 50 else None
    stretch = (float(close) / float(average) - 1) if average else None
    high_20 = prior["close"].tail(20).max() if len(prior) >= 20 else None
    low_20 = prior["close"].tail(20).min() if len(prior) >= 20 else None
    return {
        "oi_usd": None if pd.isna(last.get("oi_usd")) else float(last["oi_usd"]),
        "volume_usd": None if pd.isna(last.get("volume_usd")) else float(last["volume_usd"]),
        "funding_pct": funding_pct,
        "volume_ratio": volume_ratio,
        "oi_change_7d": oi_change,
        "oi_at_high": oi_high,
        "stretch": stretch,
        "new_high": bool(high_20 is not None and close >= high_20),
        "new_low": bool(low_20 is not None and close <= low_20),
    }


def liquid(rows):
    """One row per coin, the venue with the most open interest, above the floor."""
    best = {}
    for row in rows:
        oi = row["readings"]["oi_usd"]
        volume = row["readings"]["volume_usd"]
        if oi is None or volume is None or oi < OI_FLOOR or volume < VOLUME_FLOOR:
            continue
        held = best.get(row["coin"])
        if held is None or oi > held["readings"]["oi_usd"]:
            best[row["coin"]] = row
    return list(best.values())


def _entry(row, value, aux):
    return {"symbol": row["coin"], "value": value, "aux": aux}


def lists_from(rows):
    """The ten lists, each capped at ten, each ranked by its own measure."""
    def funding(cut, reverse):
        pool = [row for row in rows if row["readings"]["funding_pct"] is not None
                and (row["readings"]["funding_pct"] >= cut if reverse else row["readings"]["funding_pct"] <= cut)]
        pool.sort(key=lambda row: row["readings"]["funding_pct"], reverse=reverse)
        return [_entry(row, f"{round(row['readings']['funding_pct'] * 100)}th pct",
                       f"OI {row['readings']['oi_usd'] / 1e6:.0f}M") for row in pool[:TOP]]

    def volume():
        pool = [row for row in rows if row["readings"]["volume_ratio"] is not None
                and row["readings"]["volume_ratio"] >= 1.5]
        pool.sort(key=lambda row: row["readings"]["volume_ratio"], reverse=True)
        return [_entry(row, f"{row['readings']['volume_ratio']:.1f}x median",
                       f"vol {row['readings']['volume_usd'] / 1e6:.0f}M") for row in pool[:TOP]]

    def oi(sign):
        pool = [row for row in rows if row["readings"]["oi_change_7d"] is not None
                and row["readings"]["oi_change_7d"] * sign > 0]
        pool.sort(key=lambda row: row["readings"]["oi_change_7d"] * sign, reverse=True)
        return [_entry(row, f"{row['readings']['oi_change_7d'] * 100:+.0f}% 7d",
                       f"OI {row['readings']['oi_usd'] / 1e6:.0f}M") for row in pool[:TOP]]

    def stretch(sign):
        pool = [row for row in rows if row["readings"]["stretch"] is not None
                and row["readings"]["stretch"] * sign > 0]
        pool.sort(key=lambda row: row["readings"]["stretch"] * sign, reverse=True)
        return [_entry(row, f"{row['readings']['stretch'] * 100:+.0f}% vs 50d",
                       f"OI {row['readings']['oi_usd'] / 1e6:.0f}M") for row in pool[:TOP]]

    def flagged(flag, label):
        pool = [row for row in rows if row["readings"][flag]]
        pool.sort(key=lambda row: row["readings"]["oi_usd"], reverse=True)
        return [_entry(row, label, f"OI {row['readings']['oi_usd'] / 1e6:.0f}M") for row in pool[:TOP]]

    def squeezes():
        pool = [row for row in rows if row["readings"]["oi_at_high"]
                and row["readings"]["funding_pct"] is not None
                and row["readings"]["funding_pct"] <= 0.10]
        pool.sort(key=lambda row: row["readings"]["funding_pct"])
        return [_entry(row, f"funding {round(row['readings']['funding_pct'] * 100)}th pct",
                       "OI at 60d high") for row in pool[:TOP]]

    return {
        "crowded_longs": funding(0.90, True),
        "crowded_shorts": funding(0.10, False),
        "volume_surges": volume(),
        "oi_builds": oi(1),
        "oi_flushes": oi(-1),
        "stretched_up": stretch(1),
        "stretched_down": stretch(-1),
        "new_highs": flagged("new_high", "20d high"),
        "new_lows": flagged("new_low", "20d low"),
        "squeezes": squeezes(),
    }


def build(panel=PANEL):
    """Read the panel and return the extremes payload."""
    frames = []
    for path in sorted(glob(os.path.join(panel, "*.csv"))):
        frame = pd.read_csv(path)
        if "date" not in frame.columns or frame.empty:
            continue
        frame["date"] = frame["date"].astype(str).str.slice(0, 10)
        name = os.path.basename(path)[:-4]
        exchange, symbol = name.split("_", 1)
        frame["coin"] = base_of(symbol)
        frame["venue"] = exchange
        frames.append(frame)
    if not frames:
        return {"as_of": None, "universe_n": 0, "lists": {name: [] for name in LISTS}}
    counts = {}
    for frame in frames:
        for day in set(frame["date"]):
            counts[day] = counts.get(day, 0) + 1
    day = max(counts, key=lambda d: (counts[d], d))
    rows = []
    for frame in frames:
        read = readings(frame, day)
        if read is None:
            continue
        last = frame[frame["date"] == day].iloc[-1]
        rows.append({"coin": last["coin"], "venue": last["venue"], "readings": read})
    kept = liquid(rows)
    return {"as_of": day, "universe_n": len(kept), "lists": lists_from(kept)}


def main():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from dashboard_io import write_key
    payload = build()
    write_key(OUT, payload)
    print({"as_of": payload["as_of"], "universe_n": payload["universe_n"],
           "lists": {name: len(rows) for name, rows in payload["lists"].items()}})


if __name__ == "__main__":
    main()
