"""Score pooled_drawdown_90_bottom, pre-registered as item 17.

The rule is in research/generated.md, added 2026-11-17, before this script
existed. For each name in data/panel_xs_laevitas that has a close on the
date, the factor is the close over the trailing 90-day high, and the value
ranked at day t is the prior bar's. A fire is that rank at or below the
name's own trailing one-year 10th percentile, on a bottom candidate day.
Neighbours are the 5th and the 15th. Episodes are counted once per
overlapping window across names, not once per name. The label is the
amended bottom event. This does not pull and it does not write the panel.
"""

import os
import sys

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from regime_tester.cycle_score import (  # noqa: E402
    LABELS, NEIGHBOURS, PRIMARY, clean, event_label, holds, verdict_for,
)
from regime_tester.events import rolling_percentile  # noqa: E402
from regime_tester.periods import assign_period  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402

LOOKBACK = 90
HORIZON = 30
PANEL = "data/panel_xs_laevitas"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREREG = "c9c0c759f5aff896dab8a0a03bbd366f1525c53d"


def load_rows():
    """One row per name: the lagged rank and the bottom label, read once.

    A name shorter than the label's horizon cannot have a closed window, so
    it is left out rather than scored on an empty future.
    """
    rows = []
    last = None
    panel = os.path.join(ROOT, PANEL)
    for name in sorted(os.listdir(panel)):
        if not name.endswith(".csv"):
            continue
        frame = pd.read_csv(os.path.join(panel, name), usecols=["date", "close"])
        if len(frame) < LOOKBACK + HORIZON:
            continue
        frame["date"] = pd.to_datetime(frame["date"], utc=True)
        close = frame.set_index("date")["close"].astype(float).sort_index()
        close = close[~close.index.duplicated(keep="last")]
        if close.notna().sum() < LOOKBACK + HORIZON:
            continue
        rank = rolling_percentile(factor_of(close))
        label = event_label(close, LABELS[3])
        starts = starts_of(label)
        rows.append((rank, starts))
        end = close.index.max()
        last = end if last is None or end > last else last
    return rows, last


def factor_of(close):
    """Close over the trailing 90-day high. The first 89 bars stay empty."""
    high = close.rolling(LOOKBACK, min_periods=LOOKBACK).max()
    return (close / high).rename("drawdown_90")


def fires_of(rank, close, cut):
    """An extreme reading on a bottom candidate day, both known at the prior bar."""
    label = event_label(close, LABELS[3])
    candidates = label.notna()
    return (rank.le(cut) & rank.notna() & candidates).fillna(False), label


def starts_of(label):
    true = label.fillna(False).astype(bool)
    return true & ~true.shift(1, fill_value=False)


def cluster(starts, horizon):
    """One episode per window of `horizon` days, across every name.

    Two names whose episode starts fall within the horizon of each other are
    the same move, and a window shared by many names still counts as one.
    """
    if not starts:
        return []
    starts = sorted(starts)
    groups = [[starts[0]]]
    for stamp in starts[1:]:
        if (stamp - groups[-1][0]).days <= horizon:
            groups[-1].append(stamp)
        else:
            groups.append([stamp])
    return groups


def period_of(stamp):
    """The period a start falls in, from the three fixed cuts."""
    day = str(pd.Timestamp(stamp).date())
    if day <= "2024-06-30":
        return "train"
    if day <= "2025-12-31":
        return "validation"
    return "test"


def score_cut(rows, cut):
    """Lift of clustered fires against clustered episode starts, per period.

    A fire is the rank at or below the cut on a day the label is defined,
    which is a bottom candidate day. The label is computed once per name.
    """
    fire_starts = []
    episode_starts = []
    for rank, starts in rows:
        fired = (rank.le(cut) & rank.notna()).reindex(starts.index).fillna(False)
        taken = starts[starts]
        for stamp in taken.index:
            episode_starts.append(stamp)
        for stamp in taken[fired.reindex(taken.index).fillna(False)].index:
            fire_starts.append(stamp)
    by_period = {}
    for period in ("train", "validation", "test"):
        episodes = cluster(
            [s for s in episode_starts if period_of(s) == period], HORIZON)
        caught = cluster(
            [s for s in fire_starts if period_of(s) == period], HORIZON)
        n = len(episodes)
        hits = len(caught)
        lift = (hits / n) if n else None
        by_period[period] = {
            "episodes": n, "fires": hits, "lift": lift,
        }
    return by_period


def verdict_of(primary, neighbours):
    """The amended bar, on the pooled episode count rather than the day count."""
    train = primary["train"]["episodes"] + primary["validation"]["episodes"]
    if train < 30:
        return "insufficient"
    train_lift = primary["train"]["lift"]
    val_lift = primary["validation"]["lift"]
    if train_lift is None or val_lift is None:
        return "insufficient"
    if (train_lift - 1) * (val_lift - 1) <= 0 or val_lift <= 1:
        return "rejected"
    for other in neighbours:
        other_lift = other["validation"]["lift"]
        if other_lift is None or (val_lift - 1) * (other_lift - 1) <= 0:
            return "rejected"
    test_n = primary["test"]["episodes"]
    if test_n >= 10:
        test_lift = primary["test"]["lift"]
        if test_lift is None or (test_lift - 1) * (val_lift - 1) <= 0:
            return "rejected"
    return "admitted, test pending" if test_n < 10 else "admitted"


def lookahead_holds(close):
    """A price change after day t must leave the factor and its rank at t unchanged."""
    t = len(close) // 2
    factor = factor_of(close)
    rank = rolling_percentile(factor)
    perturbed = close.copy()
    perturbed.iloc[t + 1:] = perturbed.iloc[t + 1:] + 1.0
    return bool(factor.iloc[:t + 1].equals(factor_of(perturbed).iloc[:t + 1])) and bool(
        rank.iloc[:t + 1].equals(rolling_percentile(factor_of(perturbed)).iloc[:t + 1]))


def main():
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows, last = load_rows()
    print(f"names={len(rows)} panel_end={last.date()}", flush=True)
    probe = pd.read_csv(
        os.path.join(ROOT, PANEL, "binance_BTCUSDT.csv"), usecols=["date", "close"])
    probe["date"] = pd.to_datetime(probe["date"], utc=True)
    probe_close = probe.set_index("date")["close"].astype(float).sort_index()
    holds_probe = lookahead_holds(probe_close)
    cuts = {}
    for cut in (PRIMARY["bottom"],) + NEIGHBOURS["bottom"]:
        cuts[str(cut)] = score_cut(rows, cut)
        print(f"cut={cut} {cuts[str(cut)]}", flush=True)
    primary = cuts[str(PRIMARY["bottom"])]
    neighbours = [cuts[str(cut)] for cut in NEIGHBOURS["bottom"]]
    verdict = verdict_of(primary, neighbours)
    out = {
        "item": "D22",
        "today": today,
        "panel_end": str(last.date()),
        "names": len(rows),
        "panel": PANEL,
        "survivor_biased": True,
        "survivor_bias_note": "the universe is today's listings applied backward; "
                              "a name is in on a date only if its file has a close",
        "rule": "close over trailing 90-day high, prior bar, at or below the "
                "name's own trailing one-year percentile, on a bottom candidate day",
        "label": "amended bottom event B(30, 20, 7) on candidate days",
        "horizon_days": HORIZON,
        "primary_cut": PRIMARY["bottom"],
        "neighbours": list(NEIGHBOURS["bottom"]),
        "episodes_counted": "once per overlapping window across names",
        "by_cut": cuts,
        "lookahead_passed": holds_probe,
        "prereg_commit": PREREG,
        "verdict": verdict,
    }
    path = write_result("pooled_drawdown_90_bottom", clean(out), inputs=[PANEL])
    print(path)
    print(f"verdict={verdict}")


if __name__ == "__main__":
    main()
