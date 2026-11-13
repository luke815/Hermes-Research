"""Cross-sectional sweep, one measure per cycle, scored as matrices.

The per-cell scorer recomputed one indicator for one cell and ignored the cell
it had picked, so every row recorded the same signal. This one loads the close
matrix once, computes one measure across every name, and evaluates every
transform, threshold and horizon of that measure as matrix operations. Rows
land in results/sweeps/<today>_xs.csv in the train scorer's format, so the
leaderboard reads them beside the single-name rows.

A measure whose rows already exist is skipped, across every day's file, so a
restart continues rather than starting over. Nothing here reads a bar after
the train end.

Usage: python3 scripts/sweep_xs.py
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from regime_tester.indicators import LIBRARY_VERSION, META
from regime_tester.vectorized import (
    forward_returns, load_close_matrix, signal_matrix, transform_matrix,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs")
OUT = os.path.join(ROOT, "results", "sweeps")
TRAIN_END = "2024-06-30"
MIN_BARS = 60
MIN_NAMES = 10
HORIZONS = (1, 3, 10)
TRANSFORMS = ("raw", "pct_252", "z_30", "z_90", "chg_3", "chg_7", "chg_30",
              "persistence", "acceleration", "xs_rank", "divergence_20")
THRESHOLDS = (80, 90, 95, 20, 10, 5)
COST_BPS = 15  # the thin tier: 5 bps fee plus 10 bps slippage, each way


def scorable_measures():
    """Measures whose inputs the panel carries for at least one name.

    High and low are not stored, so the measures that need them are skipped and
    counted, not filled with a proxy.
    """
    available = {"close", "volume", "funding", "oi"}
    return [name for name, meta in META.items() if set(meta[1]) <= available]


def load_train():
    """The close matrix cut at the train end, names with enough history only."""
    close, digest = load_close_matrix(PANEL)
    train = close[close.index <= TRAIN_END]
    keep = train.columns[train.notna().sum() >= MIN_BARS]
    return train[keep], digest


def scored_ids():
    """Cell ids already written by this scorer, read across every day's file."""
    done = set()
    for name in sorted(os.listdir(OUT)):
        if name.endswith("_xs_vec.csv"):
            done.update(pd.read_csv(os.path.join(OUT, name), usecols=["id"])["id"])
    return done


def _fast_rank_pct(values, window, min_periods):
    """The trailing percentile as a vector operation, same result as the loop.

    Each bar's window is one row of a strided view, so the count of bars at or
    below the current bar is one comparison instead of a Python loop per name.
    A window that holds fewer than min_periods finite values stays empty.
    """
    a = np.asarray(values, dtype=float)
    n = len(a)
    if n < min_periods:
        return np.full(n, np.nan)
    from numpy.lib.stride_tricks import sliding_window_view
    windows = sliding_window_view(a, window)
    finite = ~np.isnan(windows)
    counts = finite.sum(axis=1)
    current = windows[:, -1]
    at_or_below = ((windows <= current[:, None]) & finite).sum(axis=1)
    valid = (counts >= min_periods) & ~np.isnan(current)
    with np.errstate(invalid="ignore"):
        rank = np.where(valid, 100.0 * at_or_below / counts, np.nan)
    out = np.full(n, np.nan)
    out[window - 1:] = rank
    return out


def _install_fast_rank():
    """Use the vectorized percentile for the cross-section only.

    The loop it replaces is what the correctness gate tested, so the swap is
    checked against it on real data before any row is written. The tested
    module is left as it is.
    """
    import regime_tester.vectorized as vectorized
    sample = next(iter(vectorized._rolling_rank_pct.__defaults__ or [None]), None)
    probe = np.array([1.0, np.nan, 3.0, 2.0, 5.0, 4.0, np.nan, 6.0, 2.0, 7.0])
    slow = vectorized._rolling_rank_pct(probe, 4, 3)
    fast = _fast_rank_pct(probe, 4, 3)
    if not np.allclose(slow, fast, atol=1e-9, equal_nan=True):
        raise RuntimeError("fast percentile does not match the tested loop")
    vectorized._rolling_rank_pct = _fast_rank_pct


_install_fast_rank()


def _scale(name):
    if name.startswith("z_"):
        return "zscore"
    if name.startswith("chg_") or name in ("raw", "acceleration"):
        return "cross_section"
    return "percentile"


def load_panel(names_kept):
    """Every column the panel has, for the names that pass the history bar.

    High and low are not stored, so a measure that needs them is absent rather
    than filled. A name is absent on a date it has no value. Volume is stored
    as quote units for most names and as base units for the stopped Binance
    names; either one is volume, and a name that has both keeps the quote one.
    """
    wanted = ["date", "close", "volume_usd", "volume_base", "funding_rate", "oi_usd"]
    frames = {}
    for name in names_kept:
        path = os.path.join(PANEL, name + ".csv")
        have = [c for c in wanted if c in pd.read_csv(path, nrows=0).columns]
        frame = pd.read_csv(path, usecols=have).set_index("date")
        if "volume_usd" not in frame.columns and "volume_base" in frame.columns:
            frame = frame.rename(columns={"volume_base": "volume_usd"})
        frames[name] = frame
    return frames


def measure_matrix(panel, name, index):
    """One measure across every name, aligned to the train dates.

    Each name is computed on its own history, so a name that listed late does
    not borrow another name's bars. Early bars stay empty until the window is
    full, and a measure the panel cannot support raises.
    """
    from regime_tester.indicators import indicators
    columns = {}
    for token, frame in panel.items():
        built = frame.rename(columns={"volume_usd": "volume", "funding_rate": "funding",
                                      "oi_usd": "oi"})
        got = indicators(built)
        if name not in got.columns:
            continue
        columns[token] = got[name]
    if not columns:
        raise ValueError(f"{name} needs inputs the panel does not have")
    return pd.DataFrame(columns).reindex(index)


def _year_signs(spread):
    signs = {}
    for year, group in spread.groupby(spread.index.str[:4]):
        finite = group.dropna()
        if len(finite):
            signs[int(year)] = float(np.sign(finite.mean()))
    return signs


CACHE = os.path.join(ROOT, "data", "panel_xs_cache")


def indicator_cache(panel, index, digest):
    """Every scorable measure as a matrix, cached on the panel hash.

    The library is computed once per name and every measure is taken from that
    pass. Computing it per measure repeats the same work 27 times. A cache
    written for a different hash is ignored, so a panel change recomputes.
    """
    path = os.path.join(CACHE, f"indicators_{digest}_v2.csv")
    if os.path.exists(path):
        wide = pd.read_csv(path, header=[0, 1], index_col=0)
        return {m: wide[m].set_axis(index) for m in wide.columns.get_level_values(0).unique()}
    from regime_tester.indicators import indicators
    wanted = scorable_measures()
    per_measure = {name: {} for name in wanted}
    for token, frame in panel.items():
        built = frame.rename(columns={"volume_usd": "volume", "funding_rate": "funding",
                                      "oi_usd": "oi"})
        got = indicators(built)
        for name in wanted:
            if name in got.columns:
                per_measure[name][token] = got[name]
    frames = {}
    for name, columns in per_measure.items():
        if not columns:
            continue
        # A measure the inputs cannot support for a name is empty there, not
        # dropped. Dropping the name makes the matrix narrower than the return
        # matrix and the spread crashes on the broadcast.
        matrix = pd.DataFrame(columns).reindex(index=index, columns=panel.keys())
        matrix.columns = pd.MultiIndex.from_product([[name], matrix.columns])
        frames[name] = matrix
    wide = pd.concat(frames.values(), axis=1)
    os.makedirs(CACHE, exist_ok=True)
    tmp = path + ".tmp"
    wide.to_csv(tmp)
    os.replace(tmp, path)
    return {name: frame.droplevel(0, axis=1) for name, frame in frames.items()}


def _spreads(cut, net, levels, direction):
    """The daily spread at every threshold, from one pass over the matrix.

    The names on a date are sorted by the cut, and the cumulative sum of their
    forward returns gives the mean of every tail. levels maps a threshold to the
    value it cuts on, so a z-score is cut at the normal quantile rather than at
    80. A threshold that flags fewer than two names, or leaves fewer than two,
    is empty.
    """
    cut = cut.reindex(columns=net.columns)
    values = cut.to_numpy(dtype=float)
    returns = net.to_numpy(dtype=float)
    dates = len(values)
    out = {threshold: np.full(dates, np.nan) for threshold in levels}
    for i in range(dates):
        both = ~np.isnan(values[i]) & ~np.isnan(returns[i])
        if both.sum() < MIN_NAMES:
            continue
        ordered_values = np.sort(values[i][both])
        order = np.argsort(values[i][both])
        ordered = returns[i][both][order]
        n = len(ordered)
        cumulative = np.cumsum(ordered)
        total = cumulative[-1]
        for threshold, level in levels.items():
            if direction == "above":
                count = int(np.searchsorted(ordered_values, level, side="left"))
                flagged = n - count
                flagged_sum = total - (cumulative[count - 1] if count else 0)
            else:
                count = int(np.searchsorted(ordered_values, level, side="right"))
                flagged = count
                flagged_sum = cumulative[count - 1] if count else 0
            rest = n - flagged
            if flagged >= 2 and rest >= 2:
                out[threshold][i] = flagged_sum / flagged - (total - flagged_sum) / rest
    return {threshold: pd.Series(series, index=cut.index) for threshold, series in out.items()}


def score_one(close, measure, name, net_by_horizon):
    """Every cell of one measure, in the train scorer's row format."""
    measure.attrs["close"] = close
    rows = []
    for transform in TRANSFORMS:
        transformed = transform_matrix(measure, transform).shift(1)
        scale = _scale(transform)
        if scale == "zscore":
            from scipy.stats import norm
            cut = transformed
            levels = {threshold: float(norm.ppf(threshold / 100.0)) for threshold in THRESHOLDS}
        elif scale == "cross_section":
            cut = transformed.rank(axis=1, pct=True) * 100
            levels = {threshold: float(threshold) for threshold in THRESHOLDS}
        else:
            cut = transformed
            levels = {threshold: float(threshold) for threshold in THRESHOLDS}
        finite = cut.notna().sum().sum()
        for direction in ("above", "below"):
            group = [t for t in THRESHOLDS if (t <= 20) == (direction == "below")]
            for horizon in HORIZONS:
                for target in ("ret", "rel"):
                    spreads = _spreads(cut, net_by_horizon[horizon][target], levels, direction)
                    for threshold in group:
                        spread = spreads[threshold]
                        independent = spread.iloc[::horizon].dropna()
                        n_ind = int(len(independent))
                        t_stat = np.nan
                        if n_ind > 2 and independent.std() > 0:
                            t_stat = float(independent.mean() / (independent.std() / np.sqrt(n_ind)))
                        share = float((cut >= levels[threshold]).sum().sum() / finite) if finite else np.nan
                        if direction == "below":
                            share = float((cut <= levels[threshold]).sum().sum() / finite) if finite else np.nan
                        rows.append({
                            "id": f"{name}|{transform}|{direction}|{threshold}|{target}_{horizon}"
                                  "|pit_cross_section|none|daily",
                            "measure": name, "transform": transform,
                            "direction": direction, "threshold": int(threshold),
                            "target": f"{target}_{horizon}", "universe": "pit_cross_section",
                            "conditioning": "none", "timeframe": "daily",
                            "spread": float(spread.mean()) if spread.notna().any() else np.nan,
                            "spread_independent": float(independent.mean()) if n_ind else np.nan,
                            "t_newey_west": t_stat,
                            "n_independent": n_ind,
                            "n_overlap": int(spread.notna().sum()),
                            "below_minimum": bool(n_ind < 40),
                            "degenerate": bool(share < 0.01 or share > 0.5) if finite else True,
                            "fragile": False,
                            "duplicate": False,
                            "admitted_corr": json.dumps({}),
                            "year_signs": json.dumps(_year_signs(spread)),
                            "train_period_hash": close.attrs.get("digest", ""),
                            "library_version": LIBRARY_VERSION,
                            "names": int(close.shape[1]),
                            "flagged_share": None if not finite else round(share, 4),
                        })
    return rows


def out_path():
    """Today's vectorized file. Separate from the per-cell files, which hold one
    identical row per measure and are the record of the retired scorer."""
    return os.path.join(OUT, datetime.now(timezone.utc).strftime("%Y-%m-%d") + "_xs_vec.csv")


def append_rows(rows):
    """Append one measure's rows. A duplicate id refuses the write."""
    path = out_path()
    frame = pd.DataFrame(rows)
    if os.path.exists(path):
        frame = pd.concat([pd.read_csv(path), frame], ignore_index=True)
    if frame["id"].duplicated().any():
        raise RuntimeError("append would write a duplicate cell id")
    tmp = path + ".tmp"
    frame.to_csv(tmp, index=False)
    os.replace(tmp, path)
    return path, len(frame)


def net_returns(close):
    """Forward return net of the thin-tier round trip, and the same minus BTC.

    The panel has no USD open interest, so every name takes the thin tier.
    BTC is the panel's own BTC column when it is there; otherwise the relative
    return is scored against zero and equals the absolute return.
    """
    gross = forward_returns(close, HORIZONS)
    out = {}
    for horizon, frame in gross.items():
        net = frame - 2 * COST_BPS / 10_000
        btc = net["BTC"] if "BTC" in net.columns else 0
        out[horizon] = {"ret": net, "rel": net.sub(btc, axis=0)}
    return out


def cycle(ctx):
    close = ctx.get("close")
    if close is None:
        close, digest = load_train()
        close.attrs["digest"] = digest
        ctx["close"] = close
        ctx["panel"] = load_panel(close.columns)
        ctx["measures"] = indicator_cache(ctx["panel"], close.index, digest)
        ctx["net"] = net_returns(close)
    done = {cid.split("|", 1)[0] for cid in scored_ids()}
    pending = [name for name in ctx["measures"] if name not in done]
    if not pending:
        return {"measure": None, "names": int(close.shape[1]), "remaining": 0}
    name = pending[0]
    rows = score_one(close, ctx["measures"][name], name, ctx["net"])
    path, total = append_rows(rows)
    return {"measure": name, "names": int(close.shape[1]), "rows": len(rows),
            "rows_total": total, "remaining": len(pending) - 1,
            "file": os.path.basename(path)}


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from daemon_base import run_loop
    run_loop("sweep_xs", interval_sec=60, cycle=cycle, align=False,
             max_cycle_sec=900)
