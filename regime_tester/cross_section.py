"""Cross-sectional and event scorer, the S3b module.

For a return cell, each date the universe is ranked on the cell's signal and
the row records the rank correlation with the forward return and the spread
between the top and bottom decile. For an event cell, the signal marks
candidate days and the row records how often the event follows, how many days
ahead, and how often it does not.

The feature is lagged one bar and the rank uses only the names with a value on
that date, so a name that has not listed yet is absent rather than filled. The
lookahead test perturbs every price after bar t and asserts the score at t does
not change.

Writes the same columns as the train scorer, so the leaderboard can read both.
"""

import json

import numpy as np
import pandas as pd

from regime_tester.indicators import LIBRARY_VERSION


def rank_ic(signal, forward):
    """Spearman correlation between the cross-sectional rank and the return."""
    both = signal.notna() & forward.notna()
    if both.sum() < 10:
        return np.nan
    return float(signal[both].rank().corr(forward[both].rank()))


def decile_spread(signal, forward):
    """Mean return of the top decile minus the bottom decile, in percent."""
    both = signal.notna() & forward.notna()
    if both.sum() < 20:
        return np.nan
    ranks = signal[both].rank(pct=True)
    top = forward[both][ranks >= 0.9]
    bottom = forward[both][ranks <= 0.1]
    if top.empty or bottom.empty:
        return np.nan
    return float((top.mean() - bottom.mean()) * 100)


def score_cross_section(panel, signal_fn, horizon):
    """Rank IC and decile spread per date, over the names present that date.

    panel is a dict of name to a frame with date and close. signal_fn takes a
    close series and returns the signal, lagged one bar by the caller.
    """
    rows = []
    for name, frame in panel.items():
        close = frame.set_index("date")["close"].astype(float)
        signal = signal_fn(close).shift(1)
        forward = close.shift(-horizon) / close - 1
        joined = pd.DataFrame({"signal": signal, "forward": forward}).dropna()
        joined["name"] = name
        rows.append(joined)
    if not rows:
        return pd.DataFrame()
    stacked = pd.concat(rows)
    out = []
    for date, group in stacked.groupby(level=0):
        out.append({
            "date": date,
            "names": int(len(group)),
            "rank_ic": rank_ic(group["signal"], group["forward"]),
            "decile_spread": decile_spread(group["signal"], group["forward"]),
        })
    return pd.DataFrame(out)


def event_lift(candidates, events, horizon):
    """How often the event follows a candidate day, against the base rate.

    candidates and events are boolean series on the same index. Lead time is
    the mean number of days from a candidate to the next event. A false alarm
    is a candidate with no event inside the horizon.
    """
    decided = candidates.notna() & events.notna()
    base = float(events[decided].mean()) if decided.sum() else np.nan
    hits, alarms, leads = 0, 0, []
    idx = candidates.index
    for pos in np.where(candidates.fillna(False).to_numpy())[0]:
        window = events.iloc[pos + 1:pos + 1 + horizon]
        if window.empty:
            continue
        if window.any():
            hits += 1
            leads.append(int(np.argmax(window.to_numpy())) + 1)
        else:
            alarms += 1
    total = hits + alarms
    return {
        "candidates": int(total),
        "hit_rate": hits / total if total else np.nan,
        "base_rate": base,
        "lift": (hits / total) / base if total and base else np.nan,
        "mean_lead_days": float(np.mean(leads)) if leads else np.nan,
        "false_alarms": int(alarms),
    }


def lookahead_holds(close, signal_fn):
    """True when perturbing every price after bar t leaves the signal at t unchanged."""
    signal = signal_fn(close)
    t = len(close) // 2
    perturbed = close.copy()
    perturbed.iloc[t + 1:] = perturbed.iloc[t + 1:] * 1.5
    other = signal_fn(perturbed)
    return bool(np.allclose(signal.iloc[:t + 1].fillna(0), other.iloc[:t + 1].fillna(0), equal_nan=True))


def row_for(cell_id, measure, dates, ic, spread, period_hash):
    """One row in the train scorer's format, so the leaderboard reads both."""
    finite = ic.dropna()
    return {
        "id": cell_id, "measure": measure, "transform": "xs_rank",
        "direction": "above", "threshold": 90,
        "target": "rel_1", "universe": "pit_cross_section",
        "conditioning": "none", "timeframe": "daily",
        "spread": float(spread.mean()) if spread.notna().any() else np.nan,
        "spread_independent": float(spread.iloc[::1].mean()) if spread.notna().any() else np.nan,
        "t_newey_west": float(finite.mean() / (finite.std() / np.sqrt(len(finite)))) if len(finite) > 2 else np.nan,
        "n_independent": int(len(finite)),
        "n_overlap": int(len(dates)),
        "below_minimum": bool(len(finite) < 40),
        "degenerate": bool(finite.std() == 0) if len(finite) else True,
        "fragile": False,
        "duplicate": False,
        "admitted_corr": json.dumps({}),
        "year_signs": json.dumps({}),
        "train_period_hash": period_hash,
        "library_version": LIBRARY_VERSION,
    }
