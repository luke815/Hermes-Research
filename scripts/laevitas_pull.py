"""Laevitas v1 history, one instrument per cycle, resumable.

Perpetuals first, then dated futures, then options contracts, then
liquidations by currency. A family opens only when the one before it has
no incomplete file, so a later pull never takes a token from an earlier
family that is still short of today. A name is marked done only when its
file is written and current, or the vendor returned 400 or 404.

Options contracts are not the expiry rows in instruments.json. Those name
an expiry, not a strike. The contract list is fetched once, when futures
are current, and saved before any option history is pulled.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rate_budget

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "data", "laevitas", "perpetuals")
FUTURES_STORE = os.path.join(ROOT, "data", "laevitas", "futures")
OPTIONS_STORE = os.path.join(ROOT, "data", "laevitas", "options")
LIQUIDATIONS_STORE = os.path.join(ROOT, "data", "laevitas", "liquidations")
INSTRUMENTS = os.path.join(ROOT, "data", "laevitas", "instruments.json")
OPTION_CONTRACTS = os.path.join(ROOT, "data", "laevitas", "option_contracts.json")
CATALOG = os.path.join(ROOT, "data", "laevitas", "catalog_v1.json")

# Currency-level liquidations, not per contract. The catalogue lists the
# venues that serve this route; the currency list is the perpetuals we hold.
LIQUIDATION_MARKETS = (
    "DERIBIT", "BINANCE", "BITFINEX", "BYBIT", "HUOBI",
    "HYPERLIQUID", "KRAKEN", "NADO", "OKX",
)


def families():
    """Looked up at call time so a test can point the stores elsewhere."""
    return (
        ("perpetual", STORE, "perpetuals"),
        ("future", FUTURES_STORE, "futures"),
        ("option", OPTIONS_STORE, "options"),
        ("liquidation", LIQUIDATIONS_STORE, "liquidation_by_currency"),
    )


def key():
    for line in open("/opt/data/.env"):
        if line.startswith("LAEVITAS_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("LAEVITAS_API_KEY missing")


def complete(path, today):
    """Done when the file holds every page, or its last bar is current.

    Files written before pages_fetched existed are complete when they reach
    today. A file that stops early is the page cap, and is refetched.
    """
    if not os.path.exists(path):
        return False
    try:
        body = json.load(open(path))
    except json.JSONDecodeError:
        return False
    if body.get("error"):
        return True
    meta = body.get("meta") or {}
    pages = meta.get("total_pages") or 1
    if body.get("pages_fetched") == pages and len(body.get("items", [])) == meta.get("total", len(body.get("items", []))):
        return True
    dates = [i.get("date") for i in body.get("items", []) if i.get("date")]
    if not dates:
        return False
    last = datetime.fromtimestamp(max(dates) / 1000, timezone.utc).strftime("%Y-%m-%d")
    return last >= today


def _load(path, default):
    if not os.path.exists(path):
        return default
    try:
        return json.load(open(path))
    except json.JSONDecodeError:
        return default


def option_rows():
    """Saved contracts, or nothing until the list has been fetched."""
    saved = _load(OPTION_CONTRACTS, [])
    return saved if isinstance(saved, list) else []


def liquidation_rows():
    """One row per venue and currency that has a perpetual."""
    perps = _load(INSTRUMENTS, [])
    currencies = sorted({r["currency"] for r in perps if r.get("type") == "perpetual" and r.get("currency")})
    return [
        {"market": market, "type": "liquidation", "instrument": currency, "currency": currency}
        for market in LIQUIDATION_MARKETS
        for currency in currencies
    ]


def rows_for(kind):
    if kind == "option":
        return option_rows()
    if kind == "liquidation":
        return liquidation_rows()
    return [r for r in _load(INSTRUMENTS, []) if r.get("type") == kind]


def pending():
    """Incomplete names of the first family that still has any.

    A later family is not listed while an earlier family is still short of
    today. Options with no saved contract list count as incomplete, so
    liquidations wait until that list exists and every contract is current.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for kind, store, _route in families():
        rows = rows_for(kind)
        if kind == "option" and not rows:
            return [{"type": "option", "instrument": None, "market": None, "list": True}]
        waiting = [r for r in rows if not complete(
            os.path.join(store, f"{r['market']}_{r['instrument']}.json"), today)]
        if waiting:
            return waiting
    return []


def fetch_option_contracts(end):
    """One maturity of one venue, appended to the saved contract list.

    The unfiltered instrument route returns 500, so each call carries a
    market, a currency and a maturity. The list is the work, not the history.
    """
    catalog = _load(CATALOG, {})
    maturities = ((catalog.get("params") or {}).get("maturities") or {}).get("data") or {}
    saved = option_rows()
    have = {(r["market"], r["instrument"]) for r in saved}
    # Resume past maturities already written. A cycle that re-walks the
    # catalogue from the start spends its token on a call that adds nothing.
    seen = {(r["market"], r.get("currency"), r.get("expiry")) for r in saved}
    for market, currencies in maturities.items():
        if not isinstance(currencies, dict):
            continue
        for currency, dates in currencies.items():
            for maturity in dates or []:
                if (market.upper(), currency, maturity) in seen:
                    continue
                url = ("https://api.laevitas.ch/analytics/options/Instruments?"
                       + urllib.parse.urlencode({
                           "market": market.upper(),
                           "currency": currency,
                           "maturity": maturity,
                       }))
                body = rate_budget.get_json(
                    url, {"apikey": key(), "User-Agent": "Mozilla/5.0"},
                    timeout=90, allowance="laevitas")
                data = body.get("data") if isinstance(body, dict) else body
                added = 0
                for row in data or []:
                    name = row.get("instrument")
                    if not name or (market.upper(), name) in have:
                        continue
                    saved.append({
                        "market": market.upper(),
                        "type": "option",
                        "currency": row.get("currency") or currency,
                        "instrument": name,
                        "expiry": row.get("maturity") or maturity,
                    })
                    have.add((market.upper(), name))
                    added += 1
                if added:
                    os.makedirs(os.path.dirname(OPTION_CONTRACTS), exist_ok=True)
                    json.dump(saved, open(OPTION_CONTRACTS, "w"))
                    return {"listed": added, "contracts": len(saved), "market": market.upper(),
                            "currency": currency, "maturity": maturity}
    os.makedirs(os.path.dirname(OPTION_CONTRACTS), exist_ok=True)
    json.dump(saved, open(OPTION_CONTRACTS, "w"))
    return {"listed": 0, "contracts": len(saved), "done": True}


def pull(row, end):
    symbol = urllib.parse.quote(row["instrument"], safe="")
    route = next(route for kind, _store, route in families() if kind == row["type"])
    market = urllib.parse.quote(row["market"], safe="")
    # Options history is not under /historical/derivs. The contract route is
    # /historical/options/{market}/{instrument}.
    if row["type"] == "option":
        base = f"https://api.laevitas.ch/historical/options/{market}/{symbol}"
    else:
        base = f"https://api.laevitas.ch/historical/derivs/{route}/{market}/{symbol}"
    meta = None
    page = 1
    pages = []
    # A name listed in 2021 is more than 2000 daily bars, so the page cap has
    # to clear that. Five pages stopped at 1000 bars and looked like a delisting.
    while page <= 20:
        url = f"{base}?start=2021-03-26&end={end}&granularity=1d&page={page}&limit=1000"
        body = rate_budget.get_json(
            url, {"apikey": key(), "User-Agent": "Mozilla/5.0"},
            timeout=60, allowance="laevitas")
        meta = body.get("meta", meta)
        pages.extend(body.get("items", []))
        total_pages = (meta or {}).get("total_pages", 1)
        if page >= total_pages:
            break
        page += 1
    return {"meta": meta, "items": pages, "pages_fetched": page}


def cycle(ctx):
    left = pending()
    if not left:
        return {"remaining": 0}
    row = left[0]
    if row.get("list"):
        end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        try:
            listed = fetch_option_contracts(end)
        except Exception as exc:  # noqa: BLE001
            print(f"skip option list: {exc}", flush=True)
            return {"skipped": 1, "remaining": len(left)}
        return {"listed": listed.get("listed", 0), "contracts": listed.get("contracts", 0),
                "remaining": len(left)}
    store = next(store for kind, store, _route in families() if kind == row["type"])
    os.makedirs(store, exist_ok=True)
    end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        body = pull(row, end)
    except urllib.error.HTTPError as exc:
        if exc.code in (400, 404):
            path = os.path.join(store, f"{row['market']}_{row['instrument']}.json")
            json.dump({"items": [], "error": exc.code}, open(path, "w"))
            return {"empty": 1, "code": exc.code, "remaining": len(left) - 1}
        print(f"skip {row['market']} {row['instrument']}: {exc}", flush=True)
        return {"skipped": 1, "remaining": len(left)}
    except Exception as exc:  # noqa: BLE001
        print(f"skip {row['market']} {row['instrument']}: {exc}", flush=True)
        return {"skipped": 1, "remaining": len(left)}
    path = os.path.join(store, f"{row['market']}_{row['instrument']}.json")
    json.dump(body, open(path, "w"))
    return {"market": row["market"], "instrument": row["instrument"],
            "rows": len(body.get("items", [])), "remaining": len(left) - 1}


if __name__ == "__main__":
    from daemon_base import run_loop
    run_loop("laevitas_pull", interval_sec=20, cycle=cycle, align=False)
