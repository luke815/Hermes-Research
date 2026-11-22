"""Daily digest payload. Reads files, writes one results file, prints the path.

The cron message quotes this file and does not recompute. Heat and the factor
legs come from regime_tester.heat.heat_score on data/panel.csv, the same
function hourly_health.py uses, so the reading matches the newest bar rather
than dashboard/data.json, which the daily refresh has not rewritten yet.
"""

import json
import os
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_tester.heat import COMPONENTS, heat_score
from regime_tester.results_io import write_result

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOW = datetime.now(timezone.utc)
TODAY = NOW.strftime("%Y-%m-%d")
WINDOW = NOW - timedelta(hours=24)
BAND = 0.40


def load(path):
    with open(os.path.join(ROOT, path)) as handle:
        return json.load(handle)


def parse_ts(text):
    return datetime.fromisoformat(str(text).replace("Z", "+00:00"))


def pid_alive(pid):
    try:
        os.kill(int(pid), 0)
    except (OSError, TypeError, ValueError):
        return False
    return True


def zone_of(value):
    if value >= BAND:
        return "hot"
    if value <= -BAND:
        return "cold"
    return "middle"


def daemons():
    configured = sorted(load("ops/daemons.json"))
    disabled_dir = os.path.join(ROOT, "ops", "disabled")
    disabled = sorted(os.listdir(disabled_dir)) if os.path.isdir(disabled_dir) else []
    alive, dead = [], []
    for name in os.listdir(os.path.join(ROOT, "ops")):
        if not name.endswith("_heartbeat"):
            continue
        daemon = name[: -len("_heartbeat")]
        if daemon not in configured:
            continue
        raw = open(os.path.join(ROOT, "ops", name)).read().strip()
        beat = None
        for _ in range(3):
            try:
                beat = json.loads(raw)
                break
            except json.JSONDecodeError:
                raw = open(os.path.join(ROOT, "ops", name)).read().strip()
        if beat is None:
            dead.append({"name": daemon, "why": "heartbeat not json"})
            continue
        age = (NOW - parse_ts(beat["ts"])).total_seconds()
        interval = beat.get("interval_sec") or 60
        stale = age > max(interval * 3, 180)
        live = pid_alive(beat.get("pid"))
        if live and not stale and beat.get("phase") != "stopped":
            alive.append(daemon)
        else:
            dead.append({
                "name": daemon,
                "phase": beat.get("phase"),
                "proc_alive": live,
                "age_s": round(age),
                "stale": stale,
            })
    return {
        "alive": len(alive),
        "configured": len(configured),
        "alive_names": sorted(alive),
        "dead": dead,
        "disabled": disabled,
        "counted_at": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def runs():
    jobs = json.load(open("/opt/data/cron/jobs.json"))["jobs"]
    names = {job["id"]: job["name"] for job in jobs}
    connection = sqlite3.connect("/opt/data/cron/executions.db")
    connection.row_factory = sqlite3.Row
    completed, other = Counter(), Counter()
    for row in connection.execute("SELECT job_id, status, started_at FROM executions"):
        if not row["started_at"]:
            continue
        started = parse_ts(row["started_at"])
        if started < WINDOW:
            continue
        name = names.get(row["job_id"], row["job_id"])
        if "digest" in name:
            continue
        if row["status"] == "completed":
            completed[name] += 1
        else:
            other[f"{name}:{row['status']}"] += 1
    return {
        "completed_24h": sum(completed.values()),
        "by_job": dict(completed),
        "other": dict(other),
        "window_start": WINDOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "/opt/data/cron/executions.db",
    }


def confirmations():
    rows = load("results/sweeps/confirmations.json")
    verdicts = Counter(row.get("verdict") for row in rows)
    recent = [
        row for row in rows
        if row.get("attempted_at") and parse_ts(row["attempted_at"]) >= WINDOW
    ]
    passed_words = {"passed", "pass", "confirmed", "admit", "admitted"}
    return {
        "file_rows": len(rows),
        "file_verdicts": dict(verdicts),
        "attempted_24h": len(recent),
        "passed_24h": sum(
            1 for row in recent if str(row.get("verdict", "")).lower() in passed_words
        ),
        "passed_ever": sum(
            1 for row in rows if str(row.get("verdict", "")).lower() in passed_words
        ),
        "latest_attempted_at": max((row.get("attempted_at") or "" for row in rows), default=None),
        "window_start": WINDOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "recent": [
            {
                "cell_id": row.get("cell_id"),
                "verdict": row.get("verdict"),
                "attempted_at": row.get("attempted_at"),
            }
            for row in recent
        ],
    }


def tested_last_day(today):
    yesterday = (NOW - timedelta(days=1)).strftime("%Y-%m-%d")
    found = []
    for line in open(os.path.join(ROOT, "research", "log.md")):
        if not line.startswith("## "):
            continue
        if "verdict:" not in line and "scored" not in line:
            continue
        if today in line or yesterday in line:
            found.append(line.strip().lstrip("# ").strip())
    if not found:
        return "none"
    return "; ".join(found)


def open_setups():
    path = os.path.join(ROOT, "signals", "ledger.csv")
    if not os.path.exists(path):
        return 0
    frame = pd.read_csv(path)
    if frame.empty or "status" not in frame.columns:
        return 0
    return int((frame["status"].astype(str).str.lower() == "open").sum())


def main():
    panel = pd.read_csv(os.path.join(ROOT, "data", "panel.csv"), index_col=0, parse_dates=True)
    panel.index = pd.to_datetime(panel.index, utc=True)
    scored = heat_score(panel)
    heat = scored["heat"].dropna()
    last_ts = heat.index[-1]
    prev_ts = heat.index[-2]
    heat_now = float(heat.iloc[-1])
    heat_prev = float(heat.iloc[-2])
    age_days = (NOW.date() - last_ts.date()).days

    legs = {}
    for name in COMPONENTS:
        series = scored[f"leg_{name}"].dropna()
        legs[name] = {
            "now": round(float(series.iloc[-1]), 4),
            "prev": round(float(series.iloc[-2]), 4),
            "delta": round(float(series.iloc[-1]) - float(series.iloc[-2]), 4),
        }
    lift = max(legs, key=lambda name: legs[name]["now"])
    drag = min(legs, key=lambda name: legs[name]["now"])
    mover = max(legs, key=lambda name: abs(legs[name]["delta"]))

    prior_path = f"results/{(NOW - timedelta(days=1)).strftime('%Y-%m-%d')}_regime-daily-digest.json"
    prior = load(prior_path)
    dashboard = load("dashboard/data.json")
    counter = load("results/sweeps/counter.json")
    cycle = dashboard.get("cycle") or {}
    book = dashboard["book"]
    zone = zone_of(heat_now)
    zone_prior = prior.get("zone")

    payload = {
        "job": "regime-daily-digest",
        "written_utc": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "today": TODAY,
        "panel_end": last_ts.date().isoformat(),
        "panel_prev": prev_ts.date().isoformat(),
        "age_days": age_days,
        "panel_rows": int(len(panel)),
        "heat": round(heat_now, 2),
        "heat_raw": heat_now,
        "heat_prior": prior.get("heat"),
        "heat_prev_bar": round(heat_prev, 4),
        "zone": zone,
        "zone_prior": zone_prior,
        "zone_changed": zone != zone_prior,
        "hot_zone_start": BAND,
        "oos_zone": heat_now >= BAND,
        "cycle_key_present": "cycle" in dashboard,
        "cycle_has_probabilities": "top_probability" in cycle or "bottom_probability" in cycle,
        "cycle_as_of": cycle.get("as_of"),
        "forecast_reported": False,
        "legs": {name: row["now"] for name, row in legs.items()},
        "legs_delta": {name: row["delta"] for name, row in legs.items()},
        "top_lift": lift,
        "top_lift_value": legs[lift]["now"],
        "top_drag": drag,
        "top_drag_value": legs[drag]["now"],
        "top_mover": mover,
        "top_mover_delta": legs[mover]["delta"],
        "dashboard_heat": dashboard.get("regime", {}).get("score"),
        "dashboard_zone": dashboard.get("regime", {}).get("zone"),
        "dashboard_panel_end": dashboard.get("panel_end"),
        "dashboard_note": (
            "dashboard/data.json regime.score is the prior daily refresh, one bar behind the panel"
        ),
        "open_setups": open_setups(),
        "setups_file": os.path.exists(os.path.join(ROOT, "signals", "setups.md")),
        "tested_last_day": tested_last_day(TODAY),
        "cells_scored": counter.get("scored"),
        "cells_testable": counter.get("testable"),
        "cells_since": counter.get("since"),
        "counter_file": "results/sweeps/counter.json",
        "daemons": daemons(),
        "runs": runs(),
        "confirmations": confirmations(),
        "book_paper_return": book["stats"]["paper_return"],
        "book_paper_since": book["stats"]["paper_since"],
        "book_as_of": book["as_of"],
        "book_lead": book["lead"],
        "dashboard_url": "https://luke815.github.io/Hermes-Dashboard-1/",
        "dashboard_url_changed": False,
        "generated_at": dashboard.get("generated_at"),
        "refresh_file_missing": not os.path.exists(
            os.path.join(ROOT, "results", f"{TODAY}_regime-daily-refresh.json")
        ),
    }
    path = write_result("regime-daily-digest", payload, inputs=[
        "data/panel.csv",
        prior_path,
        "dashboard/data.json",
        "results/sweeps/counter.json",
        "results/sweeps/confirmations.json",
        "ops/daemons.json",
        "research/log.md",
        "signals/ledger.csv",
    ])
    print(path)


if __name__ == "__main__":
    main()
