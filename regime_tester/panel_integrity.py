"""Panel file rules shared by every writer and every reader.

A file is usable only when its dates run forward, each date appears once, and
no bar closes in the future. Funding is the day's sum of settlements, stored
with the interval those settlements were taken at, never the last print of the
day. A cross-section keeps one row per base coin, from the venue with the most
volume that day.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd


def today_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def clean_frame(frame, today=None):
    """Sort by date, drop duplicate dates and any bar whose close is in the future.

    An empty frame, or one with no date column, is returned unchanged. The
    first row of a duplicated date is kept, which is the earlier print when the
    file arrived newest-first.
    """
    if frame is None or len(frame) == 0 or "date" not in frame.columns:
        return frame
    out = frame.copy()
    out["date"] = out["date"].astype(str).str.slice(0, 10)
    out = out.sort_values("date", kind="mergesort")
    out = out.drop_duplicates("date", keep="first")
    cutoff = today if today is not None else today_utc()
    # A bar is stamped with its open time, so a bar dated today is still open
    # and is not a closed day. Keep only dates strictly before the cutoff.
    out = out[out["date"] < cutoff]
    return out.reset_index(drop=True)


def assert_sorted(frame):
    """Fail when dates run backwards or repeat. A reader calls this after cleaning."""
    if frame is None or len(frame) == 0 or "date" not in getattr(frame, "columns", []):
        return
    dates = frame["date"].astype(str)
    if not dates.is_monotonic_increasing:
        raise AssertionError("dates are not sorted")
    if int(dates.duplicated().sum()):
        raise AssertionError("duplicate dates")


def sum_funding(prints, interval_hours):
    """Daily funding as the sum of the day's settlements, with the interval.

    prints is an iterable of (epoch milliseconds, rate). A day with no print is
    absent. The interval is stored beside the sum so a later reader can tell an
    8-hour venue from a 1-hour one, and the count is stored so a reader can tell
    a summed day from a single print.
    """
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    for stamp, rate in prints:
        day = datetime.fromtimestamp(int(stamp) / 1000, timezone.utc).strftime("%Y-%m-%d")
        totals[day] = totals.get(day, 0.0) + float(rate)
        counts[day] = counts.get(day, 0) + 1
    return {day: {"funding_rate": totals[day], "funding_count": counts[day],
                  "funding_interval_hours": int(interval_hours)}
            for day in totals}


def base_of(symbol):
    """Strip the quote and the multiplier so the same coin collapses to one key."""
    stem = str(symbol).split(".")[0]
    for suffix in ("_PERP", "-SWAP", "USDT", "USDC", "USD"):
        if stem.endswith(suffix) and len(stem) > len(suffix):
            stem = stem[: -len(suffix)]
            break
    stem = stem.replace("-", "").replace("_", "")
    return stem.upper()


def collapse_venues(frames, volume_column="volume_usd"):
    """One row per base coin per date, from the venue with the most volume.

    frames maps a file name to a frame with date and close. The kept row is the
    one whose volume is largest that day; a missing volume loses to any number.
    Returns the collapsed frames and the count of file names dropped.
    """
    rows = []
    for name, frame in frames.items():
        if frame is None or len(frame) == 0 or "close" not in frame.columns:
            continue
        part = frame.copy()
        part["date"] = part["date"].astype(str).str.slice(0, 10)
        part["_name"] = name
        part["_base"] = base_of(name.split("_", 1)[-1])
        if volume_column in part.columns:
            part["_volume"] = pd.to_numeric(part[volume_column], errors="coerce")
        else:
            part["_volume"] = pd.NA
        rows.append(part)
    if not rows:
        return {}, 0
    stacked = pd.concat(rows, ignore_index=True)
    stacked["_volume"] = pd.to_numeric(stacked["_volume"], errors="coerce").fillna(-1.0)
    stacked = stacked.sort_values(["_base", "date", "_volume"], ascending=[True, True, False],
                                  kind="mergesort")
    kept = stacked.drop_duplicates(["_base", "date"], keep="first")
    chosen = kept.groupby("_base")["_name"].agg(lambda s: s.mode().iloc[0])
    collapsed = {}
    for base, name in chosen.items():
        part = kept[kept["_base"] == base].drop(columns=["_name", "_base", "_volume"])
        collapsed[str(name)] = part.reset_index(drop=True)
    return collapsed, len(frames) - len(collapsed)
