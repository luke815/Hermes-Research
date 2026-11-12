"""Vectorized cross-sectional scorer, the S7 module.

The per-cell scorer recomputes the indicator for every cell. This one computes
the indicator matrix once per measure and evaluates every transform, threshold
and target of that measure as matrix operations. The correctness gate requires
its statistics to match the per-cell scorer to six decimals on a sample of
cells, and the lookahead test to pass, before it replaces that scorer.
"""

import hashlib
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "panel_xs_cache")

HORIZONS = (1, 3, 10)
TRANSFORMS = ("raw", "pct_252", "z_30", "z_90", "chg_3", "chg_7", "chg_30",
              "persistence", "acceleration", "xs_rank", "divergence_20")
THRESHOLDS = (80, 90, 95, 20, 10, 5)


def load_close_matrix(panel_dir, names=None):
    """Dates by names close matrix, and the panel hash the cache keys on."""
    files = sorted(f for f in os.listdir(panel_dir) if f.endswith(".csv"))
    frames = {}
    for name in files:
        if names and name not in names:
            continue
        frame = pd.read_csv(os.path.join(panel_dir, name), usecols=["date", "close"])
        frames[name.replace(".csv", "")] = frame.set_index("date")["close"].astype(float)
    matrix = pd.DataFrame(frames).sort_index()
    digest = hashlib.sha256(pd.util.hash_pandas_object(matrix).values.tobytes()).hexdigest()[:16]
    return matrix, digest


def forward_returns(close, horizons):
    """R_h matrices, computed once and reused across every cell."""
    return {h: close.shift(-h) / close - 1 for h in horizons}


def rank_ic_matrix(signal, forward):
    """Spearman rank IC per date, across the names present that date."""
    both = signal.notna() & forward.notna()
    s = signal.where(both).rank(axis=1)
    f = forward.where(both).rank(axis=1)
    s = s.sub(s.mean(axis=1), axis=0)
    f = f.sub(f.mean(axis=1), axis=0)
    num = (s * f).sum(axis=1)
    den = np.sqrt((s ** 2).sum(axis=1) * (f ** 2).sum(axis=1))
    out = num / den.replace(0, np.nan)
    out[both.sum(axis=1) < 10] = np.nan
    return out


def decile_spread_matrix(signal, forward):
    """Top decile mean minus bottom decile mean, per date, in percent."""
    both = signal.notna() & forward.notna()
    ranks = signal.where(both).rank(axis=1, pct=True)
    top = forward.where(ranks >= 0.9)
    bottom = forward.where(ranks <= 0.1)
    spread = (top.mean(axis=1) - bottom.mean(axis=1)) * 100
    spread[both.sum(axis=1) < 20] = np.nan
    return spread


def _rolling_rank_pct(values, window, min_periods):
    """Percentile of each bar within its own trailing window, 0 to 100.

    The window ends at the bar, matching the per-cell scorer. Early bars stay
    empty until the window holds min_periods values.
    """
    a = np.asarray(values, dtype=float)
    n = len(a)
    out = np.full(n, np.nan)
    start = min_periods - 1
    for i in range(start, n):
        if np.isnan(a[i]):
            continue
        w = a[max(0, i - window + 1):i + 1]
        w = w[~np.isnan(w)]
        if len(w) < min_periods:
            continue
        out[i] = 100.0 * np.sum(w <= a[i]) / len(w)
    return out


def _rolling_mean_std(values, window):
    """Trailing mean and population std, empty until the window is full."""
    a = np.asarray(values, dtype=float)
    n = len(a)
    mean = np.full(n, np.nan)
    std = np.full(n, np.nan)
    filled = ~np.isnan(a)
    csum = np.cumsum(np.where(filled, a, 0.0))
    csum2 = np.cumsum(np.where(filled, a * a, 0.0))
    counts = np.cumsum(filled)
    for i in range(window - 1, n):
        lo = i - window
        count = counts[i] - (counts[lo] if lo >= 0 else 0)
        if count < window:
            continue
        total = csum[i] - (csum[lo] if lo >= 0 else 0)
        total2 = csum2[i] - (csum2[lo] if lo >= 0 else 0)
        m = total / count
        var = total2 / count - m * m
        mean[i] = m
        std[i] = np.sqrt(var) if var > 0 else np.nan
    return mean, std


def transform_column(values, name, window=252, min_periods=30):
    """One trailing transform of one column. Early bars stay empty.

    Every window ends at the bar it scores, so a change to a later bar cannot
    move an earlier one. The caller lags the result by one bar before use.
    """
    a = np.asarray(values, dtype=float)
    if name == "raw":
        return a.copy()
    if name == "pct_252":
        return _rolling_rank_pct(a, window, min_periods)
    if name in ("z_30", "z_90"):
        w = 30 if name == "z_30" else 90
        mean, std = _rolling_mean_std(a, w)
        with np.errstate(divide="ignore", invalid="ignore"):
            return (a - mean) / std
    if name.startswith("chg_"):
        w = int(name.split("_")[1])
        out = np.full(len(a), np.nan)
        base = a[:-w]
        with np.errstate(divide="ignore", invalid="ignore"):
            out[w:] = np.where(base != 0, a[w:] / base - 1, np.nan)
        return out
    if name == "persistence":
        rank = _rolling_rank_pct(a, window, min_periods)
        above = rank >= 80
        out = np.zeros(len(a))
        run = 0
        for i in range(len(a)):
            run = run + 1 if above[i] else 0
            out[i] = run
        return out
    if name == "acceleration":
        d = np.diff(a, prepend=np.nan)
        out = np.full(len(a), np.nan)
        out[6:] = d[6:] - d[1:-5]
        return out
    raise ValueError(name)


def transform_matrix(measure, name, window=252, min_periods=30):
    """One transform applied per name. xs_rank and divergence need the matrix."""
    if name == "xs_rank":
        return measure.rank(axis=1, pct=True) * 100
    if name == "divergence_20":
        price = measure.attrs.get("close")
        if price is None:
            raise ValueError("divergence_20 needs the close matrix in attrs")
        sign_m = np.sign(measure - measure.shift(20))
        sign_p = np.sign(price - price.shift(20))
        return (sign_m != sign_p).where(measure.notna() & price.notna())
    out = {col: transform_column(measure[col].to_numpy(), name, window, min_periods)
           for col in measure.columns}
    return pd.DataFrame(out, index=measure.index)


def signal_matrix(transformed, threshold, direction, scale="percentile"):
    """Boolean signal from a transformed matrix. Empty bars stay empty.

    Percentile transforms are cut at the percentile itself. A z-score is cut
    at the normal quantile of the same percentile, because a z-score of 80
    never occurs and the cell would flag nothing. A change is cut at the
    cross-sectional quantile of that date, since a percent change has no
    natural level.
    """
    if scale == "percentile":
        cut = transformed
        level = threshold
    elif scale == "zscore":
        from scipy.stats import norm
        cut = transformed
        level = float(norm.ppf(threshold / 100.0))
    elif scale == "cross_section":
        cut = transformed.rank(axis=1, pct=True) * 100
        level = threshold
    else:
        raise ValueError(scale)
    flagged = cut >= level if direction == "above" else cut <= level
    return flagged.where(transformed.notna())


def newey_west_t(values, lag):
    """t-stat of a mean with Newey-West standard error, lag equal to horizon."""
    x = np.asarray(values, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 3:
        return np.nan
    mean = x.mean()
    d = x - mean
    gamma0 = np.dot(d, d) / n
    var = gamma0
    for k in range(1, min(lag, n - 1) + 1):
        var += 2 * (1 - k / (lag + 1)) * np.dot(d[k:], d[:-k]) / n
    se = np.sqrt(max(var, 0) / n)
    return float(mean / se) if se else np.nan


def return_stats(signal, forward, horizon):
    """Daily spread series, its non-overlapping t-stat, and the rank IC series.

    The spread on a date is the mean forward return of the names the signal
    flags minus the mean of the names it does not. Dates with fewer than two
    names on either side stay empty. The t-stat uses every h-th date, so an
    h-bar forward return is counted once.
    """
    flagged = signal.fillna(False).astype(bool)
    present = signal.notna() & forward.notna()
    in_state = forward.where(present & flagged)
    out_state = forward.where(present & ~flagged)
    enough = (in_state.notna().sum(axis=1) >= 2) & (out_state.notna().sum(axis=1) >= 2)
    spread = (in_state.mean(axis=1) - out_state.mean(axis=1)).where(enough)
    ic = rank_ic_matrix(signal.astype(float), forward)
    independent = spread.iloc[::horizon].dropna()
    return {
        "spread": spread,
        "rank_ic": ic,
        "mean_spread": float(spread.mean()) if spread.notna().any() else np.nan,
        "mean_rank_ic": float(ic.mean()) if ic.notna().any() else np.nan,
        "t_independent": newey_west_t(independent.to_numpy(), 1),
        "n_independent": int(len(independent)),
        "year_signs": {int(y): float(np.sign(g.mean()))
                       for y, g in spread.groupby(spread.index.str[:4])
                       if g.notna().any()},
    }


def lookahead_holds(measure_fn, close, t):
    """True when perturbing every price after day t leaves the signal at t unchanged.

    measure_fn takes a close matrix and returns the signal matrix at the bar
    the sweep would act on, already lagged. A function that fills its early
    bars with a full-sample statistic fails here.
    """
    base = measure_fn(close)
    perturbed = close.copy()
    perturbed.iloc[t + 1:] = perturbed.iloc[t + 1:] * 1.5
    other = measure_fn(perturbed)
    left = base.iloc[:t + 1].to_numpy(dtype=float)
    right = other.iloc[:t + 1].to_numpy(dtype=float)
    return bool(np.allclose(np.nan_to_num(left), np.nan_to_num(right), atol=1e-9))


def score_measure(close, measure, transforms, thresholds, horizons):
    """Every cell of one measure, as one row each. The worker entry point.

    The measure is lagged one bar before any threshold is applied, and the
    forward returns end before the last bar, so nothing here reads a bar that
    has not closed. A measure whose rows already exist for the current panel
    hash is the caller's concern; this function only scores.
    """
    returns = forward_returns(close, horizons)
    rows = []
    for name in transforms:
        if name == "divergence_20":
            measure.attrs["close"] = close
        transformed = transform_matrix(measure, name).shift(1)
        if name.startswith("z_"):
            scale = "zscore"
        elif name.startswith("chg_") or name == "raw":
            scale = "cross_section"
        else:
            scale = "percentile"
        for threshold in thresholds:
            direction = "below" if threshold <= 20 else "above"
            flagged = signal_matrix(transformed, threshold, direction, scale)
            for horizon in horizons:
                stats = return_stats(flagged, returns[horizon], horizon)
                rows.append({
                    "transform": name, "threshold": int(threshold),
                    "direction": direction, "horizon": int(horizon),
                    "mean_spread": stats["mean_spread"],
                    "mean_rank_ic": stats["mean_rank_ic"],
                    "t_independent": stats["t_independent"],
                    "n_independent": stats["n_independent"],
                })
    return rows


def score_measures_parallel(close, measures, workers):
    """One process per measure, merged in measure order.

    Each worker gets its own copy of the close matrix and writes nothing, so
    two workers cannot collide. The caller checkpoints the merged rows.
    """
    from multiprocessing import get_context
    jobs = [(close, frame, TRANSFORMS, THRESHOLDS, HORIZONS) for frame in measures.values()]
    with get_context("fork").Pool(workers) as pool:
        parts = pool.starmap(score_measure, jobs)
    return dict(zip(measures, parts))
