"""C1 rerun on the amended targets. Labels only, no factor is scored.

Top candidates are days whose close is within 5 percent of the trailing
60-day high. A top is a 20 percent drop within the next 30 days. Bottom
candidates are days within 5 percent of the trailing 60-day low. A bottom
is a 20 percent rise within 30 days with no close in between more than 7
percent below today. Also reported: a 15 percent drop within 20 days, a 30
percent drop within 60 days, and a 30 percent rise within 60 days.

Base rates are among candidate days, not all days. Episodes collapse
consecutive candidate days carrying the same label. A 20 percent zigzag
marks the last day before a reversal of that size, and the report counts
how many of those swing points the event labels catch and miss.

Usage: python3 scripts/c1_rerun.py
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from regime_tester.episodes import base_rates, bottom_event, episodes, top_event
from regime_tester.periods import assign_period

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel.csv")

ASSETS = ("btc_price", "eth_price", "alt_price")
NEAR = 0.05
LOOKBACK = 60
# Primary definitions, then the two neighbours the amendment names.
TOPS = ((30, 0.20), (20, 0.15), (60, 0.30))
BOTTOMS = ((30, 0.20, 0.07), (60, 0.30, 0.07))
ZIGZAG = 0.20


def load_panel():
    frame = pd.read_csv(PANEL, index_col=0, parse_dates=True)
    if frame.index.tz is None:
        frame.index = frame.index.tz_localize("UTC")
    return frame


def candidate_mask(close, side):
    """Days within 5 percent of the trailing 60-day extreme, bar t included.

    The extreme is a trailing statistic of closes up to today, so it does
    not read the future. The first 59 bars have no full window and are not
    candidates.
    """
    if side == "top":
        extreme = close.rolling(LOOKBACK, min_periods=LOOKBACK).max()
        return close >= extreme * (1 - NEAR)
    extreme = close.rolling(LOOKBACK, min_periods=LOOKBACK).min()
    return close <= extreme * (1 + NEAR)


def among_candidates(label, candidates, period):
    """Base rate restricted to candidate days whose window has closed.

    A candidate day whose forward window is still open is excluded from the
    denominator, the same way an undecided day is excluded everywhere else.
    An episode is attributed to the period and the year of its first day, so
    a run that crosses a boundary is counted once rather than in both.
    """
    kept = label.where(candidates.fillna(False), other=False)
    kept = kept.where(candidates & label.notna(), other=np.nan)
    rates = base_rates(kept, period)
    ids = episodes(kept.fillna(False))
    frame = pd.DataFrame({"period": period, "year": kept.index.year, "episode": ids})
    frame = frame[frame["episode"] > 0].groupby("episode").first()
    rates["episodes_by_period"] = {
        name: int((frame["period"] == name).sum()) for name in ("train", "validation", "test")}
    counts = frame.groupby("year").size()
    rates["episodes_by_year"] = {int(str(year)): int(count) for year, count in counts.items()}
    return rates


def year_share(rates):
    """Largest share of episodes sitting in one calendar year, by start date."""
    counts = rates["episodes_by_year"]
    total = sum(counts.values())
    if not total:
        return {"year": None, "share": None, "episodes": 0}
    year = max(counts, key=lambda k: counts[k])
    return {"year": int(year), "share": counts[year] / total, "episodes": total}


def zigzag_points(close, size=ZIGZAG):
    """Last day before a reversal of `size`, walking the closes once.

    A confirmed top is the highest close since the last confirmed bottom,
    recorded on the day the close has fallen `size` below it. A confirmed
    bottom is the mirror. The swing point is the day of the extreme, not
    the day the reversal was confirmed, so the label is a classification of
    history and is never used as a feature.
    """
    values = close.to_numpy(dtype=float)
    index = close.index
    tops, bottoms = [], []
    if len(values) == 0 or np.isnan(values[0]):
        return tops, bottoms
    mode = None
    extreme_i = 0
    extreme = values[0]
    for i in range(1, len(values)):
        price = values[i]
        if np.isnan(price):
            continue
        if mode is None:
            if price >= extreme * (1 + size):
                bottoms.append(index[extreme_i])
                mode, extreme, extreme_i = "up", price, i
            elif price <= extreme * (1 - size):
                tops.append(index[extreme_i])
                mode, extreme, extreme_i = "down", price, i
            elif price > extreme:
                extreme, extreme_i = price, i
            elif price < extreme:
                extreme, extreme_i = price, i
            continue
        if mode == "up":
            if price > extreme:
                extreme, extreme_i = price, i
            elif price <= extreme * (1 - size):
                tops.append(index[extreme_i])
                mode, extreme, extreme_i = "down", price, i
        else:
            if price < extreme:
                extreme, extreme_i = price, i
            elif price >= extreme * (1 + size):
                bottoms.append(index[extreme_i])
                mode, extreme, extreme_i = "up", price, i
    return tops, bottoms


def swing_check(points, label, window):
    """How many zigzag points the event label catches inside a window.

    A point is caught when the label is true on the swing day or on one of
    the `window` days before it, because the label fires while the price is
    still near the extreme and the swing point is the extreme itself. A
    point whose label window has not closed is neither a catch nor a miss.
    """
    caught = missed = open_window = 0
    dates = []
    for point in points:
        loc = label.index.searchsorted(point)
        if loc >= len(label):
            continue
        start = max(0, loc - window)
        span = label.iloc[start:loc + 1]
        if span.isna().all():
            open_window += 1
        elif bool(span.fillna(False).any()):
            caught += 1
            dates.append(str(point.date()))
        else:
            missed += 1
    return {
        "points": len(points),
        "caught": caught,
        "missed": missed,
        "open_window": open_window,
        "caught_dates": dates,
    }


def episode_rows(label, candidates):
    """One row per episode of candidate days carrying the label."""
    kept = label.where(candidates.fillna(False), other=False)
    table = episodes(kept)
    rows = []
    for episode_id, group in table[table > 0].groupby(table[table > 0]):
        rows.append({
            "episode": int(episode_id),
            "start": str(group.index.min().date()),
            "end": str(group.index.max().date()),
            "days": int(len(group)),
        })
    return rows


def one_side(close, side, period):
    candidates = candidate_mask(close, side)
    decided = candidates.fillna(False) & close.notna()
    specs = TOPS if side == "top" else BOTTOMS
    out = {
        "candidate_days": int(decided.sum()),
        "candidate_share": float(decided.mean()),
    }
    for spec in specs:
        if side == "top":
            horizon, move = spec
            label = top_event(close, horizon, move)
            name = f"T({horizon}, {int(move * 100)})"
        else:
            horizon, move, giveback = spec
            label = bottom_event(close, horizon, move, giveback)
            name = f"B({horizon}, {int(move * 100)}, {int(giveback * 100)})"
        rates = among_candidates(label, candidates, period)
        out[name] = {
            "rates": rates,
            "year_concentration": year_share(rates),
            "episodes": episode_rows(label, candidates),
        }
    return out, candidates


def lookahead_check(close):
    """Perturb every price after day t and assert the candidate flag at t holds.

    The label at t reads the next h closes by design, so the check is on the
    candidate flag, which is the only thing here that is used as a feature.
    """
    t = len(close) // 2
    flag = candidate_mask(close, "top")
    perturbed = close.copy()
    perturbed.iloc[t + 1:] = perturbed.iloc[t + 1:] * 3
    again = candidate_mask(perturbed, "top")
    return bool(flag.iloc[t] == again.iloc[t]) and bool(flag.iloc[:t].equals(again.iloc[:t]))


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    panel = load_panel()
    period = assign_period(panel.index)
    result = {
        "job": "c1_rerun",
        "date": today,
        "panel_end": str(panel.index.max().date()),
        "panel_rows": int(len(panel)),
        "rule": {
            "candidate": "close within 5 percent of the trailing 60-day extreme",
            "top": "lowest close in the next 30 days at least 20 percent below today",
            "bottom": "highest close in the next 30 days at least 20 percent above today, no close more than 7 percent below",
            "neighbours": ["T(20, 15)", "T(60, 30)", "B(60, 30, 7)"],
            "base_rate": "among candidate days whose window has closed",
        },
        "assets": {},
    }
    for asset in ASSETS:
        close = panel[asset].dropna()
        top, top_candidates = one_side(close, "top", assign_period(close.index))
        bottom, bottom_candidates = one_side(close, "bottom", assign_period(close.index))
        tops, bottoms = zigzag_points(close)
        primary_top = top_event(close, 30, 0.20)
        primary_bottom = bottom_event(close, 30, 0.20, 0.07)
        result["assets"][asset] = {
            "rows": int(len(close)),
            "top": top,
            "bottom": bottom,
            "zigzag": {
                "size": ZIGZAG,
                "tops": swing_check(tops, primary_top, 30),
                "bottoms": swing_check(bottoms, primary_bottom, 30),
            },
            "lookahead_holds": lookahead_check(close),
        }
    path = os.path.join(ROOT, "results", f"{today}_c1_rerun.json")
    json.dump(result, open(path, "w"), indent=1, default=str)
    print(path)
    for asset, block in result["assets"].items():
        top = block["top"]["T(30, 20)"]["rates"]["all"]
        bottom = block["bottom"]["B(30, 20, 7)"]["rates"]["all"]
        zig = block["zigzag"]
        print(f"{asset} candidates top {block['top']['candidate_days']} "
              f"bottom {block['bottom']['candidate_days']}")
        print(f"  T(30,20) episodes {top['episodes']} true_days {top['true_days']} "
              f"of {top['days']} rate {top['day_rate']:.4f}")
        print(f"  B(30,20,7) episodes {bottom['episodes']} true_days {bottom['true_days']} "
              f"of {bottom['days']} rate {bottom['day_rate']:.4f}")
        print(f"  zigzag tops caught {zig['tops']['caught']} of {zig['tops']['points']} "
              f"bottoms caught {zig['bottoms']['caught']} of {zig['bottoms']['points']} "
              f"lookahead {block['lookahead_holds']}")


if __name__ == "__main__":
    main()
