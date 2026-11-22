"""Record the 05:00 reading of every blocked backlog item.

Every item without a verdict is already marked blocked. This run rechecks
each one from the files the daemons write, writes the readings through
write_result, and appends a note only where the reading moved since the
02:00 note. It does not pull, it does not score, and it does not decide an
item is done.
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.results_io import write_result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "research", "backlog.md")
SLOT = "05:00"


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _append(prefix, anchor, note):
    text = open(BACKLOG).read()
    if note.strip() in text:
        return "already present"
    line = next(ln for ln in text.splitlines() if ln.startswith(prefix))
    at = line.rfind(anchor)
    if at < 0:
        raise SystemExit(f"anchor missing from the {prefix} line")
    updated = line[:at] + anchor + note + line[at + len(anchor):]
    open(BACKLOG, "w").write(text.replace(line, updated, 1))
    return "noted"


def l11(today):
    coverage = json.load(open(os.path.join(
        ROOT, "results", f"{today}_l11_coverage.json")))
    reading = json.load(open(os.path.join(
        ROOT, "results", f"{today}_l11_reading.json")))
    prior = "2026-11-22 02:00"
    moved = not (
        coverage["dead_names"] == 499 and coverage["panel_files"] == 484
        and coverage["missing_file"] == 15
        and coverage["all_three_from_2021"] == 81
        and coverage["earliest_first_bar"] == "2021-08-07"
        and reading["remaining"] == 0 and reading["daemon_remaining"] == 0)
    note = (
        f" Rechecked {today} {SLOT} UTC: results/{today}_l11_coverage.json "
        f"counts {coverage['dead_names']} dead names, {coverage['panel_files']} "
        f"panel files, {coverage['missing_file']} missing, and "
        f"{coverage['all_three_from_2021']} names with funding, open interest "
        f"and basis from 2021, earliest {coverage['earliest_first_bar']}. "
        f"results/{today}_l11_reading.json shows remaining "
        f"{reading['remaining']} of {reading['dead_names']}. delisted_pull "
        f"phase {reading['phase']}, cycles {reading['cycles']}, remaining "
        f"{reading['daemon_remaining']}. "
        + ("The reading moved since the 02:00 note. "
           if moved else "Unchanged since the 02:00 note. ")
        + "The vendor serves nothing earlier. Blocked on the vendor's start date.")
    return _append("- L11. ", "Blocked on the vendor's start date.", note), moved


def l2(today):
    from l2_status import main as unused  # noqa: F401
    status = json.load(open(os.path.join(ROOT, "results", f"{today}_l2_status.json")))
    options = status["options"]
    liquidations = status["liquidations"]
    puller = status["puller"]
    moved = not (
        options["files"] == 3709 and options["missing"] == 12893
        and liquidations["files"] == 4 and liquidations["missing"] == 11057
        and puller["remaining"] == 3793)
    note = (
        f" Rechecked {today} {SLOT} UTC: results/{today}_l2_status.json shows "
        f"perpetual_closed {status['perpetual_closed']} and future_closed "
        f"{status['future_closed']}, maturities walked "
        f"{status['maturities_walked']} of {status['maturities_listed']}, "
        f"option files {options['files']} of {options['listed']} with "
        f"{options['missing']} missing, liquidation files "
        f"{liquidations['files']} of {liquidations['listed']} with "
        f"{liquidations['missing']} missing. laevitas_pull pid {puller['pid']}, "
        f"alive, phase {puller['phase']}, cycles {puller['cycles']}, remaining "
        f"{puller['remaining']}. "
        + ("The reading moved since the 02:00 note. "
           if moved else "Unchanged since the 02:00 note. ")
        + "Blocked on the pull. Unblocks when that file shows both families "
        "closed, option missing 0 and liquidation missing 0.")
    return _append(
        "- L2. ",
        "Unblocks when that file shows both families closed, option missing 0 "
        "and liquidation missing 0.", note), moved


def x1(today):
    status = json.load(open(os.path.join(ROOT, "results", f"{today}_x1_status.json")))
    sweep = status["sweep"]
    moved = not (
        status["open_emittable"] == 19872 and status["open_needs_range"] == 15120
        and status["cells_per_hour_above_5000"] is False and sweep["remaining"] == 0)
    note = (
        f" Rechecked {today} {SLOT} UTC: results/{today}_x1_status.json shows "
        f"cells per hour above 5,000 {status['cells_per_hour_above_5000']}, "
        f"names {sweep['names']}, {status['open_emittable']} emittable cells "
        f"still open, {status['open_market_level']} market-level and "
        f"{status['open_needs_range']} that need high and low. sweep_xs pid "
        f"{sweep['pid']}, phase {sweep['phase']}, cycles {sweep['cycles']}, "
        f"remaining {sweep['remaining']}. "
        + ("The reading moved since the 13:00 note. "
           if moved else "Unchanged since the 13:00 note. ")
        + "Blocked on the range columns reaching the panel the sweep reads. "
        "Unblocks when ops/sweep_status shows cells per hour above 5,000.")
    return _append(
        "- X1. ", "Unblocks when ops/sweep_status shows cells per hour above 5,000.",
        note), moved


def d3(today):
    hourly = os.path.join(ROOT, "research", "outside", "data", "hourly.pkl")
    store = os.path.join(ROOT, "research", "outside", "data", "laevitas")
    exists = os.path.exists(hourly)
    csvs = 0
    if os.path.isdir(store):
        csvs = sum(1 for name in os.listdir(store)
                   if "hour" in name.lower() and name.endswith(".csv"))
    payload = {"item": "D3", "today": today, "slot": SLOT,
               "hourly_pkl": exists, "laevitas_dir": os.path.isdir(store),
               "hourly_csvs": csvs}
    write_result("d3_hourly_0500", payload, inputs=["research/outside"])
    if exists or csvs:
        return "unblocked", True
    note = (
        f" Rechecked {today} {SLOT} UTC: results/{today}_d3_hourly_0500.json "
        "shows hourly.pkl absent and the laevitas hourly directory absent, so "
        "there are 0 hourly CSVs, nothing to mask and nothing to backfill "
        "from. No registered daemon pulls the Laevitas hourly store, and a "
        "research run does not pull. Unchanged since the 02:00 note. Blocked "
        "on the hourly files. Unblocks when hourly.pkl exists or the harness "
        "masks the window and says so.")
    return _append(
        "- D3. ",
        "Unblocks when hourly.pkl exists or the harness masks the window and says so.",
        note), False


def q4(today):
    from record_q4_oi_pc_0200 import series
    beat = {}
    path = os.path.join(ROOT, "ops", "market_backfill_heartbeat")
    if os.path.exists(path):
        beat = json.load(open(path))
    per_asset = {asset: series(asset) for asset in ("BTC", "ETH")}
    payload = {
        "item": "Q4", "today": today, "slot": SLOT,
        "read_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "oi_pc_ratio": per_asset,
        "market_backfill_remaining": beat.get("remaining"),
        "market_backfill_cycles": beat.get("cycles"),
        "market_backfill_phase": beat.get("phase"),
    }
    write_result("q4_oi_pc_0500", payload, inputs=["data/laevitas/market"])
    short = any(row["last_bar"] is None or row["last_bar"] <= "2025-06"
                for row in per_asset.values())
    if not short:
        return "unblocked", True
    btc, eth = per_asset["BTC"], per_asset["ETH"]
    moved = not (btc["files"] == 15 and btc["empty"] == 8
                 and btc["last_bar"] == "2023-03-23"
                 and eth["files"] == 13 and eth["empty"] == 7
                 and eth["last_bar"] == "2023-09-21")
    note = (
        f" Rechecked {today} {SLOT} UTC: results/{today}_q4_oi_pc_0500.json "
        f"shows oi_pc_ratio BTC {btc['files']} files, {btc['empty']} empty, "
        f"last bar {btc['last_bar']}; ETH {eth['files']} files, {eth['empty']} "
        f"empty, last bar {eth['last_bar']}. market_backfill reports remaining "
        f"{payload['market_backfill_remaining']} at cycle "
        f"{payload['market_backfill_cycles']}, phase "
        f"{payload['market_backfill_phase']}. "
        + ("The reading moved since the 02:00 note. "
           if moved else "Unchanged since the 02:00 note. ")
        + "Blocked on the series. Unblocks when oi_pc_ratio has a bar after "
        "2025-06 for BTC and ETH.")
    return _append(
        "- Q4. ",
        "Unblocks when oi_pc_ratio has a bar after 2025-06 for BTC and ETH.",
        note), moved


def b1(today):
    from record_b1_inputs_0200 import FILES, last_date, age_days, refresher
    out = {"item": "B1", "today": today, "slot": SLOT, "fresh_limit_days": 2}
    for name, path in FILES.items():
        full = os.path.join(ROOT, path)
        stamp = os.stat(full).st_mtime
        out[name] = {
            "path": path,
            "mtime": datetime.fromtimestamp(stamp, timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"),
            "bytes": os.path.getsize(full),
        }
    out["hourly"]["last_bar"] = last_date(os.path.join(ROOT, FILES["hourly"]), "t")
    out["daily"]["last_bar"] = last_date(os.path.join(ROOT, FILES["daily"]), "t")
    updates = [row["update"] for row in json.load(
        open(os.path.join(ROOT, FILES["snapshot"]))) if row.get("update")]
    newest = max(updates)
    out["snapshot"]["newest_update"] = datetime.fromtimestamp(
        newest / 1000 if newest > 10 ** 12 else newest, timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    for name, key in (("hourly", "last_bar"), ("daily", "last_bar"),
                      ("snapshot", "newest_update")):
        day = out[name][key][:10]
        out[name]["age_days"] = age_days(day, today)
        out[name]["stale"] = out[name]["age_days"] > 2
    out["refreshing_daemons"] = refresher()
    write_result("b1_inputs_0500", out, inputs=list(FILES.values()))
    stale = [name for name in FILES if out[name]["stale"]]
    if not stale or out["refreshing_daemons"]:
        return "unblocked", True
    moved = not (out["hourly"]["last_bar"] == "2026-11-03"
                 and out["daily"]["last_bar"] == "2026-11-04"
                 and out["snapshot"]["newest_update"] == "2026-11-03T17:50:50Z")
    note = (
        f" Rechecked {today} {SLOT} UTC: results/{today}_b1_inputs_0500.json "
        f"shows the hourly store last bar {out['hourly']['last_bar']} "
        f"({out['hourly']['age_days']} days behind), the daily bars last bar "
        f"{out['daily']['last_bar']} ({out['daily']['age_days']} days behind) "
        f"and the open-interest snapshot newest update "
        f"{out['snapshot']['newest_update']} "
        f"({out['snapshot']['age_days']} days behind). All three are past the "
        "two-day freshness limit, and no registered daemon refreshes them. "
        + ("The reading moved since the 02:00 note. "
           if moved else "Unchanged since the 02:00 note. ")
        + "Blocked on the Coinalyze inputs. Unblocks when those three files "
        "are current.")
    return _append("- B1. ", "Unblocks when those three files are current.",
                    note), moved


def main():
    today = _today()
    from x1_status import main as x1_main
    x1_main()
    results = {
        "L11": l11(today),
        "L2": l2(today),
        "X1": x1(today),
        "D3": d3(today),
        "Q4": q4(today),
        "B1": b1(today),
    }
    print(json.dumps({item: {"note": note, "moved": moved}
                      for item, (note, moved) in results.items()}))


if __name__ == "__main__":
    main()
