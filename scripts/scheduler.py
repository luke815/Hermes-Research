"""Scheduler. Runs the deterministic jobs at fixed UTC times, no model involved.

Each job runs once per slot, under a lock, and writes a results file. A second
copy exits on the lock. The health check reads heartbeats and the hosted files
and posts to Telegram only when something is wrong.

Jobs, UTC:
  05:30  daily refresh
  05:45  universe re-rank
  06:15  book marks
  every hour at :05  health check

Usage: python3 scripts/scheduler.py
"""

import json
import os
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")
PY = "/opt/hermes/.venv/bin/python3"
ENV = dict(os.environ, PYTHONPATH="/opt/data/.local/lib/python3.14/site-packages")

JOBS = [
    {"name": "daily_refresh", "at": "05:30", "script": "scripts/refresh_coinalyze.py"},
    {"name": "rerank", "at": "05:45", "script": "scripts/rank_universe.py"},
    {"name": "book_marks", "at": "06:15", "script": "scripts/book_composite.py"},
    {"name": "health", "at": ":05", "script": None},
]


def slot_key(job, now):
    if job["at"].startswith(":"):
        return now.strftime("%Y-%m-%dT%H")
    return now.strftime("%Y-%m-%d")


def due(job, now):
    if job["at"].startswith(":"):
        return now.strftime("%M") == job["at"][1:]
    return now.strftime("%H:%M") == job["at"]


def already_ran(job, now):
    path = os.path.join(RESULTS, f"{now.strftime('%Y-%m-%d')}_{job['name']}.json")
    if not os.path.exists(path):
        return False
    record = json.loads(open(path).read())
    return record.get("slot") == slot_key(job, now)


def record(job, now, result):
    path = os.path.join(RESULTS, f"{now.strftime('%Y-%m-%d')}_{job['name']}.json")
    payload = {"job": job["name"], "slot": slot_key(job, now),
               "ran_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "result": result}
    tmp = path + ".tmp"
    json.dump(payload, open(tmp, "w"), indent=1)
    os.replace(tmp, path)


def run_script(script):
    proc = subprocess.run([PY, script], cwd=ROOT, env=ENV, capture_output=True, text=True, timeout=600)
    return {"exit": proc.returncode, "tail": (proc.stdout + proc.stderr)[-300:]}


def health(now):
    """Read heartbeats and the hosted file. Return the problems, or nothing."""
    problems = []
    heartbeats = {
        "supervisor": (os.path.join(ROOT, "ops", "supervisor_heartbeat"), 300),
        "live": (os.path.join(ROOT, "ops", "live_heartbeat"), 900),
    }
    for name, (path, limit) in heartbeats.items():
        try:
            data = json.loads(open(path).read())
            age = int(time.time()) - int(data.get("ts_epoch", 0))
            if age > limit:
                problems.append(f"{name} heartbeat {age}s old")
        except (OSError, json.JSONDecodeError, TypeError):
            problems.append(f"{name} heartbeat unreadable")
    try:
        url = "https://raw.githubusercontent.com/luke815/Hermes-Dashboard-1/live/live.json?t=" + str(int(time.time()))
        with urllib.request.urlopen(url, timeout=30) as resp:
            live = json.loads(resp.read())
        as_of = datetime.fromisoformat(live["as_of"].replace("Z", "+00:00"))
        lag = (now - as_of).total_seconds()
        if lag > 900:
            problems.append(f"hosted live.json {int(lag / 60)} min behind")
    except (OSError, KeyError, json.JSONDecodeError, ValueError) as exc:
        problems.append(f"hosted live.json unreadable: {exc}")
    return {"problems": problems}


def post(text):
    env = dict(line.split("=", 1) for line in open("/opt/data/.env") if "=" in line)
    token = env.get("TELEGRAM_BOT_TOKEN", "").strip().strip('"')
    if not token:
        return {"posted": False, "reason": "no token"}
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": "-1004361758177", "text": text}).encode()
    with urllib.request.urlopen(url, data=data, timeout=30) as resp:
        return {"posted": resp.status == 200}


def cycle(ctx):
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    ran = []
    for job in JOBS:
        if not due(job, now) or already_ran(job, now):
            continue
        if job["name"] == "health":
            result = health(now)
            if result["problems"]:
                result["post"] = post("health: " + "; ".join(result["problems"]))
        else:
            result = run_script(job["script"])
        record(job, now, result)
        ran.append(job["name"])
    return {"ran": ran, "minute": now.strftime("%H:%M")}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from daemon_base import run_loop
    run_loop("scheduler", interval_sec=60, cycle=cycle, align=False)
