"""Cross-sectional sweep, one measure per cycle, scored as matrices.

The per-cell scorer recomputed one indicator for one cell and ignored the cell
it had picked, so every row recorded the same signal. This one loads the close
matrix once, computes one measure across every name, and evaluates every
transform, threshold and horizon of that measure as matrix operations. Rows
land in results/sweeps/<today>_xs.csv in the train scorer's format, so the
leaderboard reads them beside the single-name rows.

The work list is results/sweeps/cross_section_cells.json, the testable
cross-section cells written by the enumerator. A measure is pending while any
of its cells on that list is unscored, read across every day's file, so a
restart continues and a daemon never reports remaining 0 while that gap exists.
The panel is data/panel_xs_laevitas, which carries basis and the long/short
ratio the positioning measures need. Nothing here reads a bar after the train
end.

Usage: python3 scripts/sweep_xs.py
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

# procmgr restarts from a clean environment, which does not have the user
# site on its path. The libraries live there, so the script adds them itself.
_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from regime_tester.counter import status_text, write_counter
from regime_tester.indicators import LIBRARY_VERSION, META
from regime_tester.vectorized import (
    forward_returns, load_close_matrix, signal_matrix, transform_matrix,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs_laevitas")
WORK = os.path.join(ROOT, "results", "sweeps", "cross_section_cells.json")
STATUS = os.path.join(ROOT, "ops", "sweep_status")
OUT = os.path.join(ROOT, "results", "sweeps")
TRAIN_END = "2024-06-30"
MIN_BARS = 60
OI_FLOOR = 20_000_000  # the book's liquidity floor, dollars of open interest
OI_FLOOR_DAYS = 60
MIN_NAMES = 10
HORIZONS = (1, 3, 10)
TRANSFORMS = ("raw", "pct_252", "z_30", "z_90", "chg_3", "chg_7", "chg_30",
              "persistence", "acceleration", "xs_rank", "divergence_20",
              "ratio_btc")
THRESHOLDS = (80, 90, 95, 20, 10, 5)
COST_BPS = 15  # the thin tier: 5 bps fee plus 10 bps slippage, each way


def scorable_measures():
    """Measures whose inputs the panel carries for at least one name.

    High and low are not stored, so the measures that need them are skipped and
    counted, not filled with a proxy.
    """
    available = {"close", "volume", "funding", "oi", "basis", "long_short_ratio"}
    return [name for name, meta in META.items() if set(meta[1]) <= available]


def load_train():
    """The close matrix cut at the train end, liquid names with enough history.

    A name clears the floor when its open interest is at least OI_FLOOR on
    OI_FLOOR_DAYS days. Two venues for one coin would count the coin twice, so
    the venue with the most days above the floor is the one that stays.
    """
    close, digest = load_close_matrix(PANEL)
    train = close[close.index <= TRAIN_END]
    enough = train.columns[train.notna().sum() >= MIN_BARS]
    liquid = liquid_names(enough)
    return train[train.columns.intersection(liquid)], digest


def liquid_names(candidates):
    """One venue per coin, among names clearing the open-interest floor."""
    best = {}
    for name in candidates:
        path = os.path.join(PANEL, name + ".csv")
        frame = pd.read_csv(path, usecols=lambda c: c in ("oi_usd",))
        if "oi_usd" not in frame.columns:
            continue
        days = int((frame["oi_usd"] >= OI_FLOOR).sum())
        if days < OI_FLOOR_DAYS:
            continue
        coin = name.split("_", 1)[1]
        if coin not in best or days > best[coin][0]:
            best[coin] = (days, name)
    return [name for days, name in best.values()]


def work_list():
    """The testable cross-section cell ids, from the enumerator's list.

    The list is the unit of work. A measure the daemon's own files happen to
    have scored is not done while one of its cells on this list is unscored.
    """
    return set(json.load(open(WORK)))


def scored_ids(names=None):
    """Cell ids already written by this scorer, read across every day's file.

    A row scored on a different name count was scored on a different universe,
    so it does not count. The liquidity floor changed the universe, and a cell
    saved before that would otherwise close the measure forever.
    """
    done = set()
    for name in sorted(os.listdir(OUT)):
        if not name.endswith("_xs_vec.csv"):
            continue
        frame = pd.read_csv(os.path.join(OUT, name), usecols=["id", "names"])
        if names is not None and "names" in frame.columns:
            frame = frame[frame["names"] == names]
        done.update(frame["id"])
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
    if name.startswith("chg_") or name in ("raw", "acceleration", "ratio_btc"):
        return "cross_section"
    return "percentile"


def emittable(cell_id):
    """A cell this scorer writes: unconditioned, daily, and a known transform.

    Conditioned variants are a different test and stay on the list uncounted.
    ratio_btc is one of the transforms, so a measure that has its other cells
    saved is still pending until those rows exist. A crossover cell is not a
    thresholded measure and is not emitted here.
    """
    parts = cell_id.split("|")
    if len(parts) < 8:
        return False
    return parts[1] in TRANSFORMS and parts[6] == "none" and parts[7] == "daily"


def pending_measures(work, done, known):
    """Measures with an emittable cell still unscored, in a stable order.

    A measure is done only when every cell this scorer can write for it is
    saved. Marking it done from any one saved cell leaves the rest of its
    transforms unwritten, and the scored count then stops moving.
    """
    open_ids = {cid for cid in work - done if emittable(cid)}
    return sorted({cid.split("|", 1)[0] for cid in open_ids if cid.split("|", 1)[0] in known})


def load_panel(names_kept):
    """Every column the panel has, for the names that pass the history bar.

    High and low are not stored, so a measure that needs them is absent rather
    than filled. A name is absent on a date it has no value. Volume is stored
    as quote units for most names and as base units for the stopped Binance
    names; either one is volume, and a name that has both keeps the quote one.
    """
    wanted = ["date", "close", "volume_usd", "volume_base", "funding_rate", "oi_usd",
              "basis", "long_short_ratio"]
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


def _spreads(cut, net, levels, direction, spans=None):
    """The daily spread at every threshold, from one pass over the matrix.

    The names on a date are sorted by the cut, and the cumulative sum of their
    forward returns gives the mean of every tail. levels maps a threshold to the
    value it cuts on, so a z-score is cut at the normal quantile rather than at
    80. A threshold that flags fewer than two names, or leaves fewer than two,
    is empty. spans drops names not listed on that date before the sort, so a
    name whose span has ended cannot move the cut.
    """
    from regime_tester.pit import apply_listing_mask
    cut = apply_listing_mask(cut.reindex(columns=net.columns), spans)
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


def score_one(close, measure, name, net_by_horizon, spans=None):
    """Every cell of one measure, in the train scorer's row format.

    spans maps a column to (listed_from, listed_to). The rank and the threshold
    cut both drop names outside their span, so a name that has not listed, or
    whose last file is past, does not enter the cross-section on that date.
    """
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
            from regime_tester.pit import apply_listing_mask
            cut = apply_listing_mask(transformed, spans).rank(axis=1, pct=True) * 100
            levels = {threshold: float(threshold) for threshold in THRESHOLDS}
        else:
            cut = transformed
            levels = {threshold: float(threshold) for threshold in THRESHOLDS}
        finite = cut.notna().sum().sum()
        for direction in ("above", "below"):
            group = [t for t in THRESHOLDS if (t <= 20) == (direction == "below")]
            for horizon in HORIZONS:
                for target in ("ret", "rel"):
                    spreads = _spreads(cut, net_by_horizon[horizon][target], levels, direction, spans)
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


def append_rows(rows, already=None):
    """Append the cells of one measure that are not already saved.

    A measure stays pending until ratio_btc is written, so the next cycle
    emits the cells the previous scorer already saved. Those are skipped.
    A duplicate inside the new rows, or against a file this call did not
    read, still refuses the write.
    """
    path = out_path()
    frame = pd.DataFrame(rows)
    if already is None:
        already = scored_ids()
    fresh = frame[~frame["id"].isin(already)]
    if fresh["id"].duplicated().any():
        raise RuntimeError("append would write a duplicate cell id")
    if os.path.exists(path):
        prior = pd.read_csv(path)
        if prior["id"].isin(fresh["id"]).any() or prior["id"].duplicated().any():
            raise RuntimeError("append would write a duplicate cell id")
        fresh = pd.concat([prior, fresh], ignore_index=True)
    tmp = path + ".tmp"
    fresh.to_csv(tmp, index=False)
    os.replace(tmp, path)
    return path, len(fresh)


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


def panel_spans(columns):
    """(listed_from, listed_to) per panel column, from the span files.

    A column is exchange_symbol. A column the span files do not name gets no
    entry, and the mask then drops it on every date rather than keeping it.
    """
    from regime_tester.pit import span_rows
    universe = span_rows()
    spans = {}
    for row in universe.itertuples(index=False):
        spans[f"{row.exchange}_{row.symbol}"] = (row.listed_from, row.listed_to)
    return {column: spans[column] for column in columns if column in spans}


def cells_this_hour():
    """Cells written to this sweep's files in the last hour, from file mtimes.

    Counting from the process's own memory reads zero after every restart, so
    the rate is read from the files instead.
    """
    cutoff = time.time() - 3600
    total = 0
    for name in os.listdir(OUT):
        if not name.endswith("_xs_vec.csv"):
            continue
        path = os.path.join(OUT, name)
        if os.path.getmtime(path) < cutoff:
            continue
        with open(path) as handle:
            total += max(sum(1 for _ in handle) - 1, 0)
    return total


def status_line(done, work, names=None, rows_this_hour=None):
    """The shared counter, with this sweep's name count and hourly rate.

    The counter number is unchanged, so the digest and this line still cite one
    file. The name count and the cells scored in the last hour are what shows
    whether the sweep is covering the panel and moving.
    """
    del done, work
    payload = write_counter()
    line = status_text(payload)
    if names is not None:
        line += f", names {names}"
    if rows_this_hour is not None:
        line += f", cells per hour {rows_this_hour}"
    tmp = STATUS + ".tmp"
    open(tmp, "w").write(line + "\n")
    os.replace(tmp, STATUS)
    return line


def cycle(ctx):
    close = ctx.get("close")
    if close is None:
        close, digest = load_train()
        close.attrs["digest"] = digest
        ctx["close"] = close
        ctx["panel"] = load_panel(close.columns)
        ctx["measures"] = indicator_cache(ctx["panel"], close.index, digest)
        ctx["net"] = net_returns(close)
        ctx["spans"] = panel_spans(close.columns)
    # The enumerator rewrites the work list while this daemon runs. Reading it
    # once at the start scores the list as it was then and never sees the rest.
    ctx["work"] = work_list()
    done = scored_ids(names=int(close.shape[1]))
    line = status_line(done, ctx["work"], names=int(close.shape[1]),
                       rows_this_hour=cells_this_hour())
    # Conditioned cells are a different test and are not counted as pending.
    # A measure stays pending until every unconditioned cell this scorer emits
    # is saved, including ratio_btc. Marking it done from any saved cell skips
    # that transform and the scored count stops moving.
    pending = pending_measures(ctx["work"], done, ctx["measures"])
    if not pending:
        return {"measure": None, "names": int(close.shape[1]), "remaining": 0,
                "status_line": line}
    name = pending[0]
    rows = score_one(close, ctx["measures"][name], name, ctx["net"], ctx["spans"])
    path, total = append_rows(rows, already=done)
    return {"measure": name, "names": int(close.shape[1]), "rows": len(rows),
            "rows_total": total, "remaining": len(pending) - 1,
            "status_line": line, "file": os.path.basename(path)}


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from daemon_base import run_loop
    run_loop("sweep_xs", interval_sec=60, cycle=cycle, align=False,
             max_cycle_sec=900)
