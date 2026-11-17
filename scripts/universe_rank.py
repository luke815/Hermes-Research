"""Universe ranking. The composite on every name with enough history.

Three components, each z-scored across names before the equal-weight average:
14-day and 30-day return relative to BTC, and position in the trailing-year
range. Raw returns (often +100 percent on a small name) used to be averaged
with a 0-to-1 range position, so one pumped name topped the table whatever its
trend. Tokenized stocks, ETFs and commodities are excluded: they are not part
of the crypto cross-section. A name that fails a long or short rule gets the
first reason it failed. Writes the universe_rank key of dashboard/data.json.

Usage: python3 scripts/universe_rank.py
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dashboard_io import update_keys  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs")
KEY = os.path.join(ROOT, "dashboard", "keys", "universe_rank.json")


# Tokenized equities, ETFs, indices and commodities listed as USDT perps.
NOT_CRYPTO = {
    "AAPL", "AMZN", "AMD", "AVGO", "BABA", "COIN", "CRCL", "CRWV", "GOOGL", "HOOD", "INTC",
    "META", "MRVL", "MSFT", "MSTR", "MU", "NBIS", "NVDA", "ORCL", "TSLA", "TSM", "PLTR", "NFLX",
    "SPY", "QQQ", "SOXL", "SOXS", "TQQQ", "EWY", "NVDL", "TSLL", "IWM", "DIA",
    "XAU", "XAG", "XAUT", "PAXG", "CL", "BZ", "NATGAS", "COPPER", "XPT", "XPD",
    "HK0700", "TENCENT", "SAMSUNG", "SKHYNIX", "SKHY", "ZHIPU", "ZHONGJI", "UNITREE",
    "ANTHROPIC", "OPENAI", "SPCX", "DRAM", "SNDK", "AAOI", "BMNR", "STRC", "CBRS", "INTW",
    "BTCDOM", "BTC",
}
EQUITY_LIKE = re.compile(r"^(HK\d{4}|\d{6})$")


def is_crypto(symbol):
    return symbol not in NOT_CRYPTO and not EQUITY_LIKE.match(symbol)


def ret(close, days):
    return close.iloc[-1] / close.iloc[-1 - days] - 1 if len(close) > days else None


def zscores(rows, key):
    vals = [r[key] for r in rows if r.get(key) is not None]
    if len(vals) < 5:
        return {}
    mean = sum(vals) / len(vals)
    sd = (sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5 or 1.0
    return {id(r): (r[key] - mean) / sd for r in rows if r.get(key) is not None}


def score_name(frame, btc=None):
    close = frame["close"].dropna()
    if len(close) < 50:
        return None
    last = close.iloc[-1]
    rs_14, rs_30 = ret(close, 14), ret(close, 30)
    if btc is not None:
        # relative to BTC over the same dates; a missing BTC bar leaves the name absolute
        b14, b30 = ret(btc.loc[:close.index[-1]], 14), ret(btc.loc[:close.index[-1]], 30)
        rs_14 = rs_14 - b14 if rs_14 is not None and b14 is not None else rs_14
        rs_30 = rs_30 - b30 if rs_30 is not None and b30 is not None else rs_30
    ma20 = close.iloc[-20:].mean()
    ma50 = close.iloc[-50:].mean()
    high = close.iloc[-365:].max()
    low = close.iloc[-365:].min()
    range_pos = (last - low) / (high - low) if high > low else None
    funding = frame["funding_rate"].dropna() if "funding_rate" in frame else pd.Series(dtype=float)
    funding_pct = float((funding.iloc[-365:] <= funding.iloc[-1]).mean()) if len(funding) > 30 else None
    return {
        "_rs_14": rs_14, "_rs_30": rs_30, "_range_pos": range_pos,
        "rs_14": round(rs_14 * 100, 1) if rs_14 is not None else None,
        "rs_30": round(rs_30 * 100, 1) if rs_30 is not None else None,
        "range_pos": round(range_pos, 3) if range_pos is not None else None,
        "funding_pct": round(funding_pct, 3) if funding_pct is not None else None,
        "above_both": bool(last > ma20 and last > ma50),
        "below_both": bool(last < ma20 and last < ma50),
    }


def main():
    universe = {r["base"]: r for r in json.load(open(os.path.join(ROOT, "data", "book_universe.json")))["rows"]}
    rows = []
    seen, skipped_floor, skipped_history, skipped_delisted, skipped_tradfi = 0, 0, 0, 0, 0
    btc_frame = pd.read_csv(os.path.join(PANEL, "binance_BTCUSDT.csv"))
    btc = btc_frame.set_index("date")["close"].dropna().sort_index()
    btc = btc[~btc.index.duplicated(keep="last")]
    for name in sorted(os.listdir(PANEL)):
        if "binance_" not in name:
            skipped_delisted += 1
            continue
        frame = pd.read_csv(os.path.join(PANEL, name))
        if "close" not in frame.columns or frame["close"].notna().sum() < 90:
            skipped_history += 1
            continue
        base = name.replace(".csv", "").split("_", 1)[-1].replace("USDT", "")
        if not is_crypto(base):
            skipped_tradfi += 1
            continue
        info = universe.get(base, {})
        oi = info.get("oi_usd") or 0
        vol = info.get("volume_24h") or 0
        if not info or oi < 20_000_000 or vol < 15_000_000:
            skipped_floor += 1
            continue
        seen += 1
        if "date" in frame:
            frame = frame.set_index("date").sort_index()
            frame = frame[~frame.index.duplicated(keep="last")]
        scored = score_name(frame, btc)
        if not scored:
            continue
        symbol = name.replace(".csv", "").split("_", 1)[-1].replace("USDT", "").replace("-SWAP", "")
        long_ok = scored["above_both"] and (scored["funding_pct"] is None or scored["funding_pct"] < 0.8)
        short_ok = scored["below_both"] and scored["funding_pct"] is not None and scored["funding_pct"] >= 0.5
        reasons = ""
        if not long_ok and not short_ok:
            reasons = "below both averages" if not scored["above_both"] else "funding crowded"
        rows.append({"symbol": symbol, "_rs_14": scored["_rs_14"], "_rs_30": scored["_rs_30"],
                     "_range_pos": scored["_range_pos"], "rs_14": scored["rs_14"],
                     "rs_30": scored["rs_30"], "range_pos": scored["range_pos"],
                     "funding_pct": scored["funding_pct"], "long_ok": long_ok,
                     "short_ok": short_ok, "reasons": reasons})
    parts = [zscores(rows, k) for k in ("_rs_14", "_rs_30", "_range_pos")]
    for row in rows:
        got = [p[id(row)] for p in parts if id(row) in p]
        row["score"] = round(sum(got) / len(got), 3) if got else None
    rows = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows if r["score"] is not None]
    rows.sort(key=lambda r: r["score"], reverse=True)
    n = len(rows)
    for i, row in enumerate(rows):
        row["decile"] = min(10, i * 10 // n + 1)
    payload = {"as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
               "note": ("Equal weights of three z-scores across names: 14-day and 30-day return "
                        "relative to BTC, and trailing-year range position. Funding percentile "
                        "gates the long and short rules but is not in the score. Stocks, ETFs "
                        "and commodities excluded. Not a tested signal."),
               "rs_basis": "vs_btc",
               "rows": rows}
    update_keys(DATA, {"universe_rank": payload})
    print(f"ranked {len(rows)} of {seen + skipped_floor + skipped_history} live names, "
          f"skipped {skipped_floor} below the liquidity floor, {skipped_history} under 90 days, "
          f"{skipped_delisted} not on binance, {skipped_tradfi} stocks, ETFs or commodities")


if __name__ == "__main__":
    main()
