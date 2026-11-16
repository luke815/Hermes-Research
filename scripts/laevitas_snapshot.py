"""Daily snapshot of the Laevitas realtime-only analytics.

The instruction of 2026-11-16 names six series that the historical endpoints do
not carry: gamma exposure by strike, open interest by strike, max pain, the IV
table, trade summaries and top traded. Each is fetched once a day per option
venue and currency and stored under data/laevitas/daily_snapshots/<date>/. The
date comes from the clock, never a literal, and a day already saved is skipped,
so a second run the same day writes nothing.

Max pain is not its own endpoint. It is computed here from the open interest by
strike, which is the same quantity the historical max-pain series reports, and
stored beside that file with the method named in it.

The trade summary returns several megabytes of individual trades. The file
keeps the per-strategy totals and the largest trades, and records how many
trades the response held, so the stored file stays small without dropping the
series.
"""

import json
import os
import sys
import urllib.parse
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rate_budget

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "data", "laevitas", "daily_snapshots")
INSTRUMENTS = os.path.join(ROOT, "data", "laevitas", "instruments.json")
BASE = "https://api.laevitas.ch"
FORWARD_FROM = "2026-11-17"

SERIES = {
    "gex_by_strike": "/analytics/options/gex_date_all/{market}/{currency}",
    "oi_by_strike": "/analytics/options/oi_strike_all/{market}/{currency}",
    "iv_table": "/analytics/options/iv_table/{market}/{currency}",
    "top_traded": "/analytics/options/top_traded_option/{market}/{currency}",
}
# The catalogue restricts this route to deribit. Other venues return 400.
DERIBIT_ONLY = {
    "trade_summary": "/analytics/options/summary_trades/{market}/{currency}/24",
}


def key():
    for line in open("/opt/data/.env"):
        if line.startswith("LAEVITAS_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("LAEVITAS_API_KEY missing")


def pairs():
    """Option venues and currencies the realtime routes actually serve.

    The catalogue lists deribit, binance, bybit, okx and paradex for these
    routes. Bullish, derive and gate have options but every realtime route
    returns 400 for them, so they are not fetched.
    """
    rows = json.load(open(INSTRUMENTS))
    served = {"deribit", "binance", "bybit", "okx", "paradex"}
    return sorted({(r["market"], r["currency"]) for r in rows
                   if r["type"] == "option" and r["currency"] in ("BTC", "ETH")
                   and r["market"] in served})


def max_pain(strikes):
    """The strike where the total intrinsic payout to holders is smallest.

    Call holders are paid max(settlement - strike, 0) times their open
    interest, put holders the reverse. The strike that minimises the sum is
    the max pain. Open interest is in contracts, so the payout is in the same
    unit and the minimum does not depend on scaling it.
    """
    levels = [s for s in strikes if isinstance(s, dict) and "strike" in s]
    if not levels:
        return None
    best, lowest = None, None
    for settle in levels:
        payout = 0.0
        for s in levels:
            payout += s.get("c", 0) * max(settle["strike"] - s["strike"], 0)
            payout += s.get("p", 0) * max(s["strike"] - settle["strike"], 0)
        if lowest is None or payout < lowest:
            best, lowest = settle["strike"], payout
    return best


def rows_of(body):
    """The strike rows, whether the file holds the raw response or a wrapped one."""
    data = body.get("data") if isinstance(body, dict) else None
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return data["data"]
    return None


def compact_trades(body):
    """Per-strategy totals plus the largest trades, not the whole tape."""
    out = {}
    for strategy, block in body.items():
        if not isinstance(block, dict):
            continue
        trades = block.get("trades") or block.get("data") or []
        if isinstance(trades, dict):
            trades = list(trades.values())
        sized = sorted(
            (t for t in trades if isinstance(t, dict)),
            key=lambda t: t.get("volume_usd") or t.get("amount") or 0,
            reverse=True)
        out[strategy] = {
            "count": len(trades),
            "fields": sorted(block.keys()),
            "largest": sized[:5],
        }
    return out


def fetch(path):
    url = BASE + path
    return rate_budget.get_json(url, {"apikey": key(), "User-Agent": "Mozilla/5.0"},
                                 timeout=90, allowance="laevitas")


def one(day, market, currency):
    """Fetch the six series for one venue and currency. Returns the file count."""
    folder = os.path.join(STORE, day)
    os.makedirs(folder, exist_ok=True)
    written, errors = 0, []
    oi = None
    for name, template in {**SERIES, **DERIBIT_ONLY}.items():
        if name in DERIBIT_ONLY and market != "deribit":
            continue
        path = os.path.join(folder, f"{name}_{market}_{currency}.json")
        if os.path.exists(path):
            if name == "oi_by_strike":
                oi = rows_of(json.load(open(path)).get("body"))
            continue
        try:
            body = fetch(template.format(market=market, currency=currency))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
            continue
        payload = {
            "forward_history_from": FORWARD_FROM,
            "captured_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "market": market,
            "currency": currency,
            "source": template.format(market=market, currency=currency),
            "body": compact_trades(body) if name == "trade_summary" else body,
        }
        tmp = path + ".tmp"
        json.dump(payload, open(tmp, "w"))
        os.replace(tmp, path)
        written += 1
        if name == "oi_by_strike":
            oi = rows_of(body)
    pain_path = os.path.join(folder, f"max_pain_{market}_{currency}.json")
    if oi is not None and not os.path.exists(pain_path):
        payload = {
            "forward_history_from": FORWARD_FROM,
            "captured_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "market": market,
            "currency": currency,
            "method": "strike minimising total intrinsic payout on oi_by_strike",
            "max_pain": max_pain(oi),
        }
        tmp = pain_path + ".tmp"
        json.dump(payload, open(tmp, "w"))
        os.replace(tmp, pain_path)
        written += 1
    return written, errors


def run():
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    done, failed = [], []
    for market, currency in pairs():
        try:
            files, errors = one(day, market, currency)
            done.append({"market": market, "currency": currency,
                         "files": files, "errors": errors})
        except Exception as exc:  # noqa: BLE001
            failed.append({"market": market, "currency": currency,
                           "error": f"{type(exc).__name__}: {exc}"})
            print(f"skip {market} {currency}: {exc}", flush=True)
    return {"day": day, "pairs": len(done) + len(failed),
            "written": done, "failed": failed}


if __name__ == "__main__":
    result = run()
    out = os.path.join(ROOT, "results", f"{result['day']}_laevitas_snapshot.json")
    json.dump(result, open(out, "w"), indent=1)
    print(json.dumps({"day": result["day"], "pairs": result["pairs"],
                      "failed": len(result["failed"]),
                      "files": sum(d["files"] for d in result["written"])}))
