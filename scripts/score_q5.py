"""Score the pre-registered Q5 crowded-shorts family.

The rules are research/outside/PREREG_Q5.md, committed before this script
existed. The alt excess is reported twice: against the pool's own mean, and
with BTC's return subtracted.
"""

import json
import os
import subprocess
import sys

_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.periods import PERIODS  # noqa: E402
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREREG = "research/outside/PREREG_Q5.md"
PANEL_XS = os.path.join(ROOT, "data", "panel_xs_laevitas")
HORIZONS = (3, 5)
EPISODE_BAR = 20
PERCENTILE_WINDOW = 365
PERCENTILE_MIN = 252
Z_WINDOW = 30
CUT = 0.1
MEMBERS = ("btc_binance", "btc_oiw", "btc_z30", "eth_binance", "alts")


def prereg_commit():
    added = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=%H", "--", PREREG],
        cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    if len(added) != 1:
        raise SystemExit(f"pre-registration was added in {len(added)} commits")
    commit = added[0]
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
        check=True).stdout.strip()
    if head == commit:
        raise SystemExit("scoring in the same commit as the pre-registration")
    return commit


def load_panel():
    """One frame per coin, the venue with the most funding bars."""
    frames = {}
    for name in sorted(os.listdir(PANEL_XS)):
        if not name.endswith(".csv"):
            continue
        venue, symbol = name[:-4].split("_", 1)
        coin = symbol.split("USDT")[0].split("-")[0]
        if not coin or coin in ("USDT", "USDC", "USD"):
            continue
        frame = pd.read_csv(os.path.join(PANEL_XS, name), usecols=[
            "date", "close", "funding_rate", "oi_usd"])
        frame = frame.dropna(subset=["funding_rate"])
        if frame.empty:
            continue
        frame["date"] = pd.to_datetime(frame["date"], utc=True)
        frame = frame.set_index("date").sort_index()
        frame = frame[~frame.index.duplicated(keep="last")]
        prior = frames.get(coin)
        if prior is None or len(frame) > prior[0]:
            frames[coin] = (len(frame), venue, frame)
    return {coin: (venue, frame) for coin, (length, venue, frame) in frames.items()}


def trailing_percentile(series):
    """Rank against the preceding window, the current bar excluded."""
    history = series.shift(1)
    return history.rolling(PERCENTILE_WINDOW, min_periods=PERCENTILE_MIN).rank(pct=True)


def trailing_z(series):
    """Z-score against the preceding window, the current bar excluded."""
    history = series.shift(1)
    mean = history.rolling(Z_WINDOW, min_periods=Z_WINDOW).mean()
    std = history.rolling(Z_WINDOW, min_periods=Z_WINDOW).std()
    return (series - mean) / std.where(std > 0)


def forward_return(price, horizon):
    return price.shift(-horizon) / price - 1


def window_of(index, start, end):
    dates = pd.Series(pd.to_datetime(index).strftime("%Y-%m-%d"), index=index)
    mask = pd.Series(True, index=index)
    if start is not None:
        mask = mask & (dates >= start)
    if end is not None:
        mask = mask & (dates <= end)
    return mask


def episodes(flag, start, end):
    flagged = flag.fillna(False).astype(bool)
    starts = flagged & ~flagged.shift(1, fill_value=False)
    return int((starts & window_of(flag.index, start, end)).sum())


def effect(flag, target, start, end):
    mask = window_of(flag.index, start, end) & flag.notna() & target.notna()
    flagged = flag[mask].fillna(False).astype(bool)
    values = target[mask].replace([np.inf, -np.inf], np.nan).dropna()
    flagged = flagged.reindex(values.index).fillna(False).astype(bool)
    row = {"n": int(len(values)), "flagged": int(flagged.sum())}
    if flagged.sum() >= 3:
        row["excess"] = round(float(values[flagged].mean() - values.mean()), 6)
    return row


def verdict_of(periods, counts):
    held = [periods.get(name, {}) for name in ("validation", "test")]
    if any("excess" not in row for row in held):
        return "insufficient"
    if counts["train"] + counts["validation"] < EPISODE_BAR:
        return "insufficient"
    signs = [row["excess"] > 0 for row in held]
    if signs[0] != signs[1]:
        return "rejected"
    return "kept"


def flag_of(funding, rule):
    if rule == "z30":
        return trailing_z(funding).le(-2)
    return trailing_percentile(funding).le(CUT)


def single(name, funding, price, rule):
    flag = flag_of(funding, rule)
    rows = []
    for horizon in HORIZONS:
        target = forward_return(price, horizon)
        periods = {}
        counts = {}
        for period, start, end in PERIODS:
            row = effect(flag, target, start, end)
            row["episodes"] = episodes(flag, start, end)
            periods[period] = row
            counts[period] = row["episodes"]
        rows.append({
            "member": name, "horizon": horizon, "periods": periods,
            "verdict": verdict_of(periods, counts),
        })
    return rows


def oiw_funding(frames, coin):
    """Open-interest-weighted funding across every venue file for one coin."""
    parts = []
    for name in sorted(os.listdir(PANEL_XS)):
        if not name.endswith(".csv") or coin not in name:
            continue
        symbol = name[:-4].split("_", 1)[1]
        if not symbol.startswith(coin):
            continue
        frame = pd.read_csv(os.path.join(PANEL_XS, name), usecols=[
            "date", "funding_rate", "oi_usd"])
        frame["date"] = pd.to_datetime(frame["date"], utc=True)
        frame = frame.dropna(subset=["funding_rate"]).set_index("date")
        parts.append(frame)
    if not parts:
        return None
    joined = pd.concat(parts)
    grouped = joined.groupby(joined.index)
    weight = grouped["oi_usd"].sum()
    weighted = (joined["funding_rate"] * joined["oi_usd"]).groupby(joined.index).sum()
    return (weighted / weight).sort_index()


def alt_pool(panels, btc_price):
    """The percentile rule on every alt, pooled by date."""
    flags = []
    returns = {horizon: [] for horizon in HORIZONS}
    btc_return = {horizon: forward_return(btc_price, horizon) for horizon in HORIZONS}
    for coin, (venue, frame) in panels.items():
        if coin in ("BTC", "ETH"):
            continue
        funding = frame["funding_rate"].astype(float)
        flag = flag_of(funding, "percentile")
        flags.append(flag.rename(coin))
        for horizon in HORIZONS:
            returns[horizon].append(forward_return(frame["close"].astype(float), horizon).rename(coin))
    flag_frame = pd.concat(flags, axis=1)
    rows = []
    for horizon in HORIZONS:
        target = pd.concat(returns[horizon], axis=1).reindex(flag_frame.index)
        btc = btc_return[horizon].reindex(flag_frame.index)
        periods = {}
        counts = {}
        for period, start, end in PERIODS:
            mask = window_of(flag_frame.index, start, end)
            flagged = flag_frame[mask].to_numpy(dtype=float)
            values = target[mask].to_numpy(dtype=float)
            values[~np.isfinite(values)] = np.nan
            defined = ~np.isnan(flagged) & ~np.isnan(values)
            fired = defined & (flagged == 1)
            row = {"n": int(defined.sum()), "flagged": int(fired.sum())}
            if fired.sum() >= 3:
                excess = float(np.nanmean(values[fired]) - np.nanmean(values[defined]))
                row["excess"] = round(excess, 6)
                subtracted = values - btc[mask].to_numpy(dtype=float)[:, None]
                defined_sub = defined & ~np.isnan(subtracted)
                fired_sub = fired & ~np.isnan(subtracted)
                if fired_sub.sum() >= 3 and defined_sub.sum():
                    row["excess_minus_btc"] = round(float(
                        np.nanmean(subtracted[fired_sub]) - np.nanmean(subtracted[defined_sub])), 6)
            any_flag = pd.Series((flag_frame.fillna(0) > 0).any(axis=1))
            row["episodes"] = episodes(any_flag, start, end)
            periods[period] = row
            counts[period] = row["episodes"]
        deciding = {
            name: {"excess": row.get("excess_minus_btc")} if "excess_minus_btc" in row else {}
            for name, row in periods.items()
        }
        rows.append({
            "member": "alts", "horizon": horizon, "periods": periods,
            "verdict": verdict_of(deciding, counts),
        })
    return rows


def main():
    commit = prereg_commit()
    panels = load_panel()
    btc_venue, btc = panels["BTC"]
    eth_venue, eth = panels["ETH"]
    rows = []
    rows += single("btc_binance", btc["funding_rate"].astype(float),
                   btc["close"].astype(float), "percentile")
    rows += single("eth_binance", eth["funding_rate"].astype(float),
                   eth["close"].astype(float), "percentile")
    rows += single("btc_z30", btc["funding_rate"].astype(float),
                   btc["close"].astype(float), "z30")
    weighted = oiw_funding(panels, "BTC")
    rows += single("btc_oiw", weighted, btc["close"].astype(float), "percentile")
    rows += alt_pool(panels, btc["close"].astype(float))
    payload = {
        "prereg_commit": commit,
        "btc_venue": btc_venue,
        "eth_venue": eth_venue,
        "alt_names": sum(1 for coin in panels if coin not in ("BTC", "ETH")),
        "members": list(MEMBERS),
        "cells": rows,
    }
    path = write_result("q5_crowded_shorts", payload,
                        inputs=["data/panel_xs_laevitas", PREREG])
    print(json.dumps({"path": path, "alts": payload["alt_names"],
                      "verdicts": [row["verdict"] for row in rows]}))


if __name__ == "__main__":
    main()
