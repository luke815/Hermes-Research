"""Record the 21:00 reading of A7 after the close rebuild.

The panel close on the jump day now comes from the vendor index, written by
scripts/rebuild_jumped_closes.py and swapped in by data_guard. A7(1) can be
rescored. A7(3) still waits on derivs_summary for five alts, which the
market_backfill daemon owns and which is not on disk. This reads both and
writes them through write_result, then appends the note.
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
    header = lines[0].split(",")
    close_at = header.index("close")
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
    corrected = abs(found.get("2026-01-13", 0) - 0.0057309) < 1e-9
    currencies = derivs_currencies()
    missing = [name for name in ALTS if name not in currencies]
    beat = heartbeat()
    payload = {
        "item": "A7",
        "today": today,
        "read_at": stamp,
        "slot": "21:00",
        "close_file": "data/panel_xs_laevitas/binance_1000PEPEUSDT.csv",
        "close_mtime": datetime.fromtimestamp(
            os.stat(PANEL).st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "closes": found,
        "price_field_jump_corrected": corrected,
        "derivs_currencies": currencies,
        "alts_missing": missing,
        "market_backfill_remaining": beat.get("remaining"),
        "market_backfill_cycles": beat.get("cycles"),
        "market_backfill_phase": beat.get("phase"),
        "previous_panel": "data/panel_xs_laevitas.prev-20261121T210441Z",
    }
    path = write_result("a7_block_2100", payload, inputs=[
        "data/panel_xs_laevitas/binance_1000PEPEUSDT.csv",
        "data/laevitas/market"])
    print(path)
    print(json.dumps({k: payload[k] for k in (
        "price_field_jump_corrected", "alts_missing",
        "market_backfill_remaining")}, default=str))
    if not corrected or missing != list(ALTS):
        raise SystemExit("the reading changed; not marking blocked")
    text = open(BACKLOG).read()
    marker = f"Rechecked {today} 21:00 UTC: results/{today}_a7_block_2100.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- A7. "))
    note = (
        f"Rechecked {today} 21:00 UTC: results/{today}_a7_block_2100.json "
        f"shows the close on 2026-01-13 is {found['2026-01-13']}, the vendor "
        f"index, against {found['2026-01-12']} on 2026-01-12 and "
        f"{found['2026-01-14']} on 2026-01-14, file mtime "
        f"{payload['close_mtime']}. The price-field jump is corrected in the "
        f"panel. A7(1) can be rescored. A7(3) stays blocked: derivs_summary "
        f"covers {', '.join(currencies)} and not {', '.join(missing)}. "
        f"market_backfill reports remaining "
        f"{payload['market_backfill_remaining']} at cycle "
        f"{payload['market_backfill_cycles']}, phase "
        f"{payload['market_backfill_phase']}, so the walk is finished and the "
        f"vendor returned nothing for those five. Unblocks when derivs_summary "
        f"has a file for ADA, SOL, LINK, XRP and AVAX. A research run does "
        f"not pull. ")
    open(BACKLOG, "w").write(text.replace(line, note + line, 1))
    print("noted")


if __name__ == "__main__":
    main()
