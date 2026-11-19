"""Call funding_sum.write_sum for one name per cycle, so the sums exist.

Nothing else calls write_sum, which is why Binance, Bybit and live OKX funding
is never summed. One name a cycle, resumable, through the shared rate bucket
that write_sum already reads.
"""

import os
import sys

# procmgr restarts from a clean environment, which does not have the user
# site on its path. The libraries live there, so the script adds them itself.
_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
import funding_sum

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "funding_sum")


def pending():
    universe = pd.read_csv(os.path.join(ROOT, "data", "universe.csv"))
    live = universe[universe.delisted == 0]
    have = set(os.listdir(OUT)) if os.path.isdir(OUT) else set()
    return [(row.exchange, row.symbol) for row in live.itertuples()
            if f"{row.exchange}_{row.symbol}.csv" not in have]


def cycle(ctx):
    left = pending()
    if not left:
        return {"remaining": 0}
    exchange, symbol = left[0]
    try:
        path, rows = funding_sum.write_sum(exchange, symbol)
    except Exception as exc:  # noqa: BLE001
        print(f"skip {exchange} {symbol}: {exc}", flush=True)
        return {"skipped": 1, "remaining": len(left) - 1}
    return {"exchange": exchange, "symbol": symbol, "rows": rows, "remaining": len(left) - 1}


if __name__ == "__main__":
    from daemon_base import run_loop
    run_loop("funding_sum", interval_sec=3, cycle=cycle, align=False)
