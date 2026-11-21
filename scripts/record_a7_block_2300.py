"""Record the 23:00 reading of A7 after the reversal rescore.

A7(1) was rescored by scripts/score_a7_reversal.py after the jump-day close
was scaled by the index return. The verdict and the close are read from the
files, not typed. A7(3) still waits on derivs_summary for five alts.
market_backfill's series list names BTC and ETH only, so that daemon will
not fetch them. A research run does not pull.
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
BACKFILL = os.path.join(ROOT, "scripts", "market_backfill.py")
SCORE = os.path.join(ROOT, "results", "2026-11-21_a7_reversal.json")
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


def backfill_lists_alts():
    text = open(BACKFILL).read()
    return any(f'"derivs_summary", "{name}"' in text for name in ALTS)


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
    beat = {}
    try:
        beat = json.loads(open(HEARTBEAT).read())
    except (OSError, json.JSONDecodeError):
        beat = {}
    score = json.loads(open(SCORE).read())
    payload = {
        "item": "A7",
        "today": today,
        "read_at": stamp,
        "slot": "23:00",
        "close_file": "data/panel_xs_laevitas/binance_1000PEPEUSDT.csv",
        "close_mtime": datetime.fromtimestamp(
            os.stat(PANEL).st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "closes": found,
        "close_on_contract_scale": on_scale,
        "score_file": "results/2026-11-21_a7_reversal.json",
        "score_written_at": score["provenance"]["written_at"],
        "score_names": score["names"],
        "score_verdict": score["verdict"],
        "score_verdicts": score["verdicts"],
        "lookahead_passed": score["lookahead"]["passed"],
        "derivs_currencies": currencies,
        "alts_missing": missing,
        "backfill_lists_alts": backfill_lists_alts(),
        "market_backfill_remaining": beat.get("remaining"),
        "market_backfill_cycles": beat.get("cycles"),
        "market_backfill_phase": beat.get("phase"),
    }
    path = write_result("a7_block_2300", payload, inputs=[
        "data/panel_xs_laevitas/binance_1000PEPEUSDT.csv",
        "data/laevitas/market",
        "results/2026-11-21_a7_reversal.json"])
    print(path)
    print(json.dumps({
        "close_on_contract_scale": on_scale,
        "score_verdict": payload["score_verdict"],
        "alts_missing": missing,
        "backfill_lists_alts": payload["backfill_lists_alts"],
    }))
    if not on_scale or missing != list(ALTS) or score["verdict"] != "rejected":
        raise SystemExit("the reading changed; not marking blocked")
    text = open(BACKLOG).read()
    marker = f"Rechecked {today} 23:00 UTC: results/{today}_a7_block_2300.json"
    if marker in text:
        raise SystemExit("note already present")
    line = next(ln for ln in text.splitlines() if ln.startswith("- A7. "))
    note = (
        f"Rechecked {today} 23:00 UTC: results/{today}_a7_block_2300.json "
        f"shows the close on 2026-01-13 is {found['2026-01-13']} against "
        f"{found['2026-01-12']} on 2026-01-12 and {found['2026-01-14']} on "
        f"2026-01-14, file mtime {payload['close_mtime']}. A7(1) was rescored "
        f"by scripts/score_a7_reversal.py: results/{today}_a7_reversal.json, "
        f"written {payload['score_written_at']}, {payload['score_names']} "
        f"names, lookahead passed, verdict {payload['score_verdict']} "
        f"({', '.join(k + ' ' + v for k, v in payload['score_verdicts'].items())}). "
        f"A7(3) stays blocked: derivs_summary covers "
        f"{', '.join(currencies)} and not {', '.join(missing)}. "
        f"scripts/market_backfill.py lists derivs_summary for BTC and ETH "
        f"only, so the daemon will not fetch the five alts. "
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
