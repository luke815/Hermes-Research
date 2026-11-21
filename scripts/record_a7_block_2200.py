"""Record the 22:00 reading of A7 after the scale fix.

The 21:00 rebuild wrote the raw vendor index on a jump day, which on a
1000-coin contract is the coin price and stays about a thousand times the
neighbouring bars. This run scales a jump day by the index return instead.
The panel close is read here, not typed. A7(3) still waits on
derivs_summary for five alts, which market_backfill owns and which is not
on disk. A research run does not pull.
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel_xs_laevitas", "binance_1000PEPEUSDT.csv")
MARKET = os.path.join(ROOT, "data", "laevitas", "market")
HEARTBEAT = os.path.join(ROOT, "ops", "market_backfill_heartbeat")
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
DATES = ("2026-01-12", "2026-01-13", "2026-01-14")
ALTS = ("ADA", "SOL", "LINK", "XRP", "AVAX")


def closes():
    lines = open(PANEL).read().splitlines()
    close_at = lines[0].split(",").index("close")
    found = {}
    for line in lines[1:]:
        row = line.split(",")
        if row[0] in DATES:
            found[row[0]] = float(row[close_at])
    return found


def derivs_currencies():
    found = set()
    for name in os.listdir(MARKET):
        if name.startswith("derivs_summary_"):
            found.add(name.split("_")[2])
    return sorted(found)


def heartbeat():
    try:
        return json.loads(open(HEARTBEAT).read())
    except (OSError, json.JSONDecodeError):
        return {}


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    found = closes()
    day = found.get("2026-01-13")
    on_scale = (
        day is not None and day < 1e-4
        and found.get("2026-01-12", 1) < 1e-4
        and found.get("2026-01-14", 1) < 1e-4)
    currencies = derivs_currencies()
    missing = [name for name in ALTS if name not in currencies]
    beat = heartbeat()
    payload = {
        "item": "A7",
        "today": today,
        "read_at": stamp,
        "slot": "22:00",
        "close_file": "data/panel_xs_laevitas/binance_1000PEPEUSDT.csv",
        "close_mtime": datetime.fromtimestamp(
            os.stat(PANEL).st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "closes": found,
        "close_on_contract_scale": on_scale,
        "prior_fix_wrote_raw_index": True,
        "derivs_currencies": currencies,
        "alts_missing": missing,
        "market_backfill_remaining": beat.get("remaining"),
        "market_backfill_cycles": beat.get("cycles"),
        "market_backfill_phase": beat.get("phase"),
        "previous_panel": "data/panel_xs_laevitas.prev-20261121T221758Z",
        "scale_commit": "528220c",
    }
    path = write_result("a7_block_2200", payload, inputs=[
        "data/panel_xs_laevitas/binance_1000PEPEUSDT.csv",
        "data/laevitas/market"])
    print(path)
    print(json.dumps({
        "close_on_contract_scale": on_scale,
        "closes": found,
        "alts_missing": missing,
        "market_backfill_remaining": payload["market_backfill_remaining"],
    }))
    if not on_scale or missing != list(ALTS):
        raise SystemExit("the reading changed; not marking blocked")
    text = open(BACKLOG).read()
    marker = f"Rechecked {today} 22:00 UTC: results/{today}_a7_block_2200.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- A7. "))
    note = (
        f"Rechecked {today} 22:00 UTC: results/{today}_a7_block_2200.json "
        f"shows the close on 2026-01-13 is {found['2026-01-13']} against "
        f"{found['2026-01-12']} on 2026-01-12 and {found['2026-01-14']} on "
        f"2026-01-14, file mtime {payload['close_mtime']}. The 21:00 rebuild "
        f"wrote the raw index, which is the coin price, so the close stayed "
        f"about a thousand times the neighbouring bars. A jump day is now the "
        f"prior close times the index return, and 51 files were swapped, none "
        f"removed or shrunk, previous kept as "
        f"{payload['previous_panel']}. A7(3) stays blocked: derivs_summary "
        f"covers {', '.join(currencies)} and not {', '.join(missing)}. "
        f"market_backfill reports remaining "
        f"{payload['market_backfill_remaining']} at cycle "
        f"{payload['market_backfill_cycles']}, phase "
        f"{payload['market_backfill_phase']}. Unblocks when derivs_summary "
        f"has a file for ADA, SOL, LINK, XRP and AVAX. A research run does "
        f"not pull. ")
    open(BACKLOG, "w").write(text.replace(line, note + line, 1))
    print("noted")


if __name__ == "__main__":
    main()
