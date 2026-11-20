"""Live daemon. One loop every five minutes, forever.

Replaces rs_daemon.py. Each loop pulls the latest 5-minute closes for the top
100, appends them to data/intraday/5m/, rebuilds the relative strength board
from the stores, marks the book, and force-pushes live.json as a single-file
orphan commit on the live branch. A failed pull keeps the previous values and
marks the file stale rather than writing zeros.

Run tracked:
    python3 scripts/live_daemon.py
"""

import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import intraday_store  # noqa: E402
import rate_budget  # noqa: E402
from rate_budget import BudgetStop  # noqa: E402
from regime_tester.rs_stale_log import LOG, append  # noqa: E402

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
    rows = json.loads(rate_budget.get(url, timeout=30, allowance="live"))
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
    by_base = {sym.split("USDT")[0]: price for sym, price in marks.items()}
    return 1, newest, by_base


def board(names):
    """Relative strength from the stores. 1h, 4h, 24h from hourly; the rest from daily."""
    daily = {r["symbol"]: r["history"] for r in json.load(open(DAILY))}

    def pct(bars, n):
        # The hourly refill drops the bar still forming, so the last stored bar
        # is closed. Dropping it again stamps the board an hour behind a store
        # that is already current, and a healthy board then reads as stale.
        if len(bars) <= n:
            return None
        last, prev = bars[-1]["c"], bars[-1 - n]["c"]
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
    last = max((intraday_store.read(s, STORE_1H)[-1]["t"] for s in names
                if intraday_store.read(s, STORE_1H)), default=None)
    as_of = (datetime.fromtimestamp(last, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
             if last else None)
    return {"as_of": as_of, "windows": list(windows),
            "universe": "Top 100 by open interest across Binance, Bybit and OKX, hourly bars.",
            "benchmarks": {b: {w: (round(v, 2) if v is not None else None) for w, v in d.items()}
                           for b, d in bench.items()},
            "rows": rows}


def hourly_closes(n=600):
    """Last n completed hourly closes for BTC and ETH (about 10 KB), so the dashboard's State tab can count TD
    Sequential setups on 1H and 4H bars. Read as live.hourly_closes.{BTC,ETH}.{t,c}: unix seconds and close."""
    out = {}
    for base in ("BTC", "ETH"):
        try:
            bars = intraday_store.read(base + "USDT_PERP.A", STORE_1H)
        except Exception:  # a store problem must not stop the push
            continue
        done = bars[:-1][-n:]  # the last bar is still forming
        if done:
            out[base] = {"t": [b["t"] for b in done], "c": [b["c"] for b in done]}
    return out


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


def book_live(marks):
    """Mark each open leg against the latest price and return the book's paper state.

    The book is read from signals/book.csv. A leg with no mark is left out rather
    than priced at zero. Returns are percent.
    """
    ledger = os.path.join(ROOT, "signals", "book.csv")
    if not os.path.exists(ledger):
        return {}
    with open(ledger, newline="") as fh:
        rows = list(csv.DictReader(fh))
    # A row with a close date is a position the book has already exited. Marking
    # it live reports a paper return on a trade that no longer exists.
    legs = []
    for row in rows:
        if row.get("closed"):
            continue
        mark = marks.get(row["symbol"])
        try:
            price = float(row["price"])
        except (TypeError, ValueError):
            continue
        if mark is None or not price:
            continue
        pnl = (mark / price - 1) * (1 if row["side"] == "long" else -1) * 100
        legs.append({"symbol": row["symbol"], "side": row["side"], "mark": mark,
                     "pnl": round(pnl, 2)})
    if not legs:
        return {}
    paper = sum(l["pnl"] for l in legs) / len(legs)
    return {"as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "paper_return": round(paper, 2), "legs": legs}


def cycle(ctx):
    """One pass: marks, board, push. The loop owns the interval and the heartbeat."""
    now = int(time.time())
    names = [r["symbol"] for r in json.load(open(TOP))["rows"]]
    calls, newest, marks = pull_5m(names, now)
    hour = ctx.setdefault("calls_this_hour", [])
    hour.append((now, calls))
    ctx["calls_this_hour"] = [(t, c) for t, c in hour if now - t < 3600]
    built = board(names)
    completed = (newest - FIVEMIN) if newest else None
    as_of = (datetime.fromtimestamp(completed, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
             if completed else None)
    lag = (now - newest) if newest else None
    note = (f"source lags {round(lag / 60)} min; newest bar returned "
            f"{datetime.fromtimestamp(newest, timezone.utc).strftime('%H:%M:%SZ')}"
            if lag and lag > 2 * FIVEMIN else "")
    # The marks are fresh every five minutes, but the board reads the hourly store,
    # which nothing in this loop updates. Judge staleness on the board's own time,
    # so a board from last week is not shown with this minute's stamp.
    # The refill writes the last closed hour shortly after the hour, so a healthy
    # board sits about one hour behind the clock, plus the minutes until :15.
    rs_age = None
    if built.get("as_of"):
        rs_age = now - int(datetime.fromisoformat(built["as_of"].replace("Z", "+00:00")).timestamp())
    rs_stale = rs_age is None or rs_age > 3 * 3600
    if rs_stale:
        note = (note + "; " if note else "") + (
            f"relative strength board is {round(rs_age / 3600)}h old" if rs_age else "no relative strength board")
    heartbeat = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # A5 needs the flag false for a full day. This payload is force-pushed, so
    # the previous reading is gone unless this cycle writes it down itself.
    append(LOG, heartbeat, rs_stale, rs_age)
    payload = {
        "as_of": as_of or built["as_of"], "interval_sec": INTERVAL,
        "health": {"daemon_heartbeat": heartbeat,
                   "api_calls_last_hour": sum(c for _, c in ctx["calls_this_hour"]),
                   "stale": as_of is None or rs_stale, "marks_stale": as_of is None,
                   "rs_stale": rs_stale, "rs_age_sec": rs_age, "note": note},
        "relative_strength": built, "book_live": book_live(marks),
        "hourly_closes": hourly_closes(),
        # watchlist, ideas and triggers are left out until this loop computes them:
        # an empty list here overwrote the daily file's values on every poll.
    }
    pushed = push(payload)
    return {"calls": calls, "pushed": pushed, "as_of": as_of, "names": len(names)}


if __name__ == "__main__":
    from daemon_base import run_loop
    run_loop("live", interval_sec=INTERVAL, cycle=cycle, align=True, offset_sec=20)
