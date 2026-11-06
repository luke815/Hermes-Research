"""Live daemon. One loop every five minutes, forever.

Replaces rs_daemon.py. Each loop pulls the latest 5-minute closes for the top
100, appends them to data/intraday/5m/, rebuilds the relative strength board
from the stores, marks the book, and force-pushes live.json as a single-file
orphan commit on the live branch. A failed pull keeps the previous values and
marks the file stale rather than writing zeros.

Run tracked:
    python3 scripts/live_daemon.py
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import intraday_store  # noqa: E402
import rate_budget  # noqa: E402
from rate_budget import BudgetStop  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOP = os.path.join(ROOT, "data", "universe_top100.json")
DAILY = os.path.join(ROOT, "data", "raw", "top100_daily.json")
LIVE = os.path.join(ROOT, "dashboard", "live.json")
HEARTBEAT = os.path.join(ROOT, "ops", "live_heartbeat")
REPO = os.path.join(ROOT, "dashboard")
STORE_5M = os.path.join(ROOT, "data", "intraday", "5m")
STORE_1H = os.path.join(ROOT, "data", "intraday")
INTERVAL = 300
FIVEMIN = 300


def save(path, obj):
    tmp = path + ".tmp"
    json.dump(obj, open(tmp, "w"))
    os.replace(tmp, path)


def key():
    if "COINALYZE_API_KEY" in os.environ:
        return os.environ["COINALYZE_API_KEY"]
    for line in open("/opt/data/.env"):
        if line.startswith("COINALYZE_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("no key")


def token():
    for line in open("/opt/data/.env"):
        if line.startswith("GITHUB_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("no token")


def pull_5m(names, now):
    """Marks from Binance's public premium index, one call for every symbol.

    The per-symbol kline endpoint takes about five seconds a call, so a
    hundred names cannot finish inside the five-minute interval. The premium
    index returns every symbol's mark in one call, which is what the live
    layer needs for marks and stops. No key, and nothing drawn from the
    Coinalyze budget.
    """
    url = "https://fapi.binance.com/fapi/v1/premiumIndex"
    try:
        rows = json.loads(rate_budget.get(url, allowance="live"))
    except BudgetStop as exc:
        print(f"5m pull stopped: {exc}", flush=True)
        return 0, None
    wanted = {n.split("USDT")[0] + "USDT" for n in names if n.split("USDT")[0].isascii()}
    marks = {r["symbol"]: float(r["markPrice"]) for r in rows if r["symbol"] in wanted}
    newest = now - (now % FIVEMIN)
    for symbol in names:
        base = symbol.split("USDT")[0]
        if base + "USDT" not in marks:
            continue
        intraday_store.append(symbol, [{"t": newest, "o": marks[base + "USDT"],
                                        "h": marks[base + "USDT"], "l": marks[base + "USDT"],
                                        "c": marks[base + "USDT"], "v": 0}], STORE_5M)
    print(f"5m binance: {len(marks)} marks, one call", flush=True)
    return 1, newest


def board(names):
    """Relative strength from the stores. 1h, 4h, 24h from hourly; the rest from daily."""
    daily = {r["symbol"]: r["history"] for r in json.load(open(DAILY))}

    def pct(bars, n):
        if len(bars) <= n + 1:
            return None
        done = bars[:-1]
        last, prev = done[-1]["c"], done[-1 - n]["c"]
        return (last / prev - 1) * 100 if last and prev else None

    windows = {"1h": 1, "4h": 4, "24h": 24, "7d": 7, "30d": 30, "90d": 90}

    def values(sym):
        hourly = intraday_store.read(sym, STORE_1H)
        out = {w: pct(hourly, n) for w, n in (("1h", 1), ("4h", 4), ("24h", 24))}
        out.update({w: pct(daily.get(sym, []), n) for w, n in (("7d", 7), ("30d", 30), ("90d", 90))})
        return out

    bench = {b: values(b + "USDT_PERP.A") for b in ("BTC", "ETH", "SOL")}
    rows = []
    for sym in names:
        base = sym.split("USDT")[0]
        vals = values(sym)
        rec = {"symbol": base, "ret": {}, "vs_btc": {}, "vs_eth": {}, "vs_sol": {}}
        for w, v in vals.items():
            rec["ret"][w] = round(v, 2) if v is not None else None
            for k, b in (("vs_btc", "BTC"), ("vs_eth", "ETH"), ("vs_sol", "SOL")):
                bv = bench[b][w]
                rec[k][w] = round(v - bv, 2) if v is not None and bv is not None else None
        rows.append(rec)
    last = max((intraday_store.read(s, STORE_1H)[-2]["t"] for s in names
                if len(intraday_store.read(s, STORE_1H)) > 2), default=None)
    as_of = (datetime.fromtimestamp(last, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
             if last else None)
    return {"as_of": as_of, "windows": list(windows),
            "universe": "Top 100 by open interest across Binance, Bybit and OKX, hourly bars.",
            "benchmarks": {b: {w: (round(v, 2) if v is not None else None) for w, v in d.items()}
                           for b, d in bench.items()},
            "rows": rows}


def push(payload):
    """Force-push live.json as a single-file orphan commit on the live branch."""
    save(LIVE, payload)
    secret = token()
    authed = f"https://x-access-token:{secret}@github.com/luke815/Hermes-Dashboard-1.git"
    env = dict(os.environ, GIT_AUTHOR_NAME="Hermes", GIT_AUTHOR_EMAIL="hermes@local",
               GIT_COMMITTER_NAME="Hermes", GIT_COMMITTER_EMAIL="hermes@local")
    blob = subprocess.run(["git", "hash-object", "-w", LIVE], cwd=REPO, capture_output=True,
                          text=True, check=True).stdout.strip()
    tree = subprocess.run(
        ["git", "mktree"], cwd=REPO, input=f"100644 blob {blob}\tlive.json\n",
        capture_output=True, text=True, check=True).stdout.strip()
    commit = subprocess.run(
        ["git", "commit-tree", tree, "-m", f"live {payload['as_of']}"],
        cwd=REPO, env=env, capture_output=True, text=True, check=True).stdout.strip()
    push_run = subprocess.run(["git", "push", "--force", authed, f"{commit}:refs/heads/live"],
                              cwd=REPO, capture_output=True, text=True)
    print(push_run.stderr.replace(secret, "[redacted]")[-200:], flush=True)
    return push_run.returncode == 0


def loop(calls_this_hour):
    now = int(time.time())
    names = [r["symbol"] for r in json.load(open(TOP))["rows"]]
    calls, newest = pull_5m(names, now)
    calls_this_hour.append((now, calls))
    calls_this_hour[:] = [(t, c) for t, c in calls_this_hour if now - t < 3600]
    built = board(names)
    # as_of is the last completed bar the source actually returned, not the clock.
    completed = (newest - FIVEMIN) if newest else None
    as_of = (datetime.fromtimestamp(completed, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
             if completed else None)
    lag = (now - newest) if newest else None
    note = (f"source lags {round(lag / 60)} min; newest bar returned "
            f"{datetime.fromtimestamp(newest, timezone.utc).strftime('%H:%M:%SZ')}"
            if lag and lag > 2 * FIVEMIN else "")
    payload = {
        "as_of": as_of or built["as_of"], "interval_sec": INTERVAL,
        "health": {"daemon_heartbeat": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "api_calls_last_hour": sum(c for _, c in calls_this_hour),
                   "stale": as_of is None, "note": note},
        "relative_strength": built, "book_live": {}, "watchlist": [], "ideas": [], "triggers": [],
    }
    pushed = push(payload)
    stamp = f"{as_of} calls={calls} pushed={pushed}"
    tmp = HEARTBEAT + ".tmp"
    open(tmp, "w").write(stamp + "\n")
    os.replace(tmp, HEARTBEAT)
    print(f"heartbeat {stamp}", flush=True)


def main():
    calls_this_hour = []
    while True:
        began = time.time()
        try:
            loop(calls_this_hour)
        except Exception as exc:  # noqa: BLE001
            print(f"loop error: {exc}", flush=True)
        time.sleep(max(0, INTERVAL - (time.time() - began)))


if __name__ == "__main__":
    main()
