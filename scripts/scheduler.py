"""Scheduler. Runs the deterministic jobs at fixed UTC times, no model involved.

Each job runs once per slot, under a lock, and writes a results file. A second
copy exits on the lock. The health check reads heartbeats and the hosted files
and posts to Telegram only when something is wrong.

Jobs, UTC:
  05:30  daily refresh
  05:45  universe re-rank (scripts/universe_rank.py)
  06:30  laevitas realtime snapshot
  06:40  derivatives key from the raw store
  06:45  heat_stats key from the panel
  every hour at :15  hourly store backfill for the relative-strength board
  every hour at :05  health check

A job whose script is missing, exits non-zero or times out is recorded as a
failure and reported by the next health check, instead of being recorded as
"ran". book_composite.py is not in the repo, so the book-marks job is off
until it is.

Usage: python3 scripts/scheduler.py
"""

import json
import os
import sys
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")
PY = "/opt/hermes/.venv/bin/python3"
ENV = dict(os.environ, PYTHONPATH="/opt/data/.local/lib/python3.14/site-packages")
COUNTER = os.path.join(ROOT, "results", "sweeps", "counter.json")
STATUS = os.path.join(ROOT, "ops", "sweep_status")

JOBS = [
    {"name": "daily_refresh", "at": "05:30", "script": "scripts/refresh_coinalyze.py"},
    {"name": "laevitas_refresh", "at": "05:35", "script": "scripts/laevitas_refresh.py"},
    {"name": "rerank", "at": "05:45", "script": "scripts/universe_rank.py"},
    {"name": "laevitas_snapshot", "at": "06:30", "script": "scripts/laevitas_snapshot.py", "timeout": 2400},
    {"name": "derivatives_key", "at": "06:40", "script": "scripts/build_derivatives_key.py"},
    {"name": "heat_stats", "at": "06:45", "script": "scripts/build_heat_stats.py"},
    {"name": "intraday_backfill", "at": ":15", "script": "scripts/backfill_intraday.py", "timeout": 900},
    {"name": "health", "at": ":05", "script": None},
]


def slot_key(job, now):
    if job["at"].startswith(":"):
        return now.strftime("%Y-%m-%dT%H")
    return now.strftime("%Y-%m-%d")


def due(job, now):
    """Due at its minute, and still due later in the hour if that minute was missed.

    A scheduler that was down at 05:35 runs the job on the next cycle instead
    of waiting until tomorrow. already_ran stops a second fire.
    """
    if job["at"].startswith(":"):
        return now.strftime("%M") >= job["at"][1:]
    hour, minute = job["at"].split(":")
    return now.strftime("%H") == hour and now.strftime("%M") >= minute


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


def run_script(script, timeout=600):
    if not os.path.exists(os.path.join(ROOT, script)):
        return {"exit": None, "ok": False, "tail": f"missing script {script}"}
    try:
        proc = subprocess.run([PY, script], cwd=ROOT, env=ENV, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return {"exit": None, "ok": False, "tail": f"timeout after {timeout}s: {str(exc.stdout or '')[-200:]}"}
    return {"exit": proc.returncode, "ok": proc.returncode == 0, "tail": (proc.stdout + proc.stderr)[-300:]}


def failed_jobs(now):
    """Job records from the last hour that did not finish cleanly. Each failure is reported once."""
    out = []
    for job in JOBS:
        if job["script"] is None:
            continue
        path = os.path.join(RESULTS, f"{now.strftime('%Y-%m-%d')}_{job['name']}.json")
        try:
            record_ = json.loads(open(path).read())
            ran_at = datetime.fromisoformat(record_["ran_at"].replace("Z", "+00:00"))
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            continue
        if (now - ran_at).total_seconds() > 3600:
            continue
        result = record_.get("result", {})
        if result.get("ok") is False or result.get("exit") not in (0, None):
            out.append(f"{job['name']}: {result.get('tail', '')[-120:]}")
    return out


def sweep_status():
    """Mirror the shared counter into the status line, so both cite one file."""
    if not os.path.exists(COUNTER):
        return {"wrote": False}
    payload = json.load(open(COUNTER))
    line = (f"cells scored {payload['scored']} since {payload.get('since')}, "
            f"from {payload['file']}\n")
    tmp = STATUS + ".tmp"
    open(tmp, "w").write(line)
    os.replace(tmp, STATUS)
    return {"wrote": True, "line": line.strip()}


GUARDED_DIRS = ("data/panel_xs", "data/panel_xs_laevitas")


def guard_problems():
    """Done items without a passing done_check, data that vanished, claims abused, a drifted skill."""
    out = []
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    try:
        import done_check
        out.extend(done_check.audit())
    except Exception as exc:  # noqa: BLE001
        out.append(f"done_check audit failed: {exc}")
    try:
        import data_guard
        for rel in GUARDED_DIRS:
            if os.path.isdir(os.path.join(ROOT, rel)):
                out.extend(data_guard.check(rel))
        out.extend("data loss recorded: " + line for line in data_guard.recent_losses())
    except Exception as exc:  # noqa: BLE001
        out.append(f"data_guard check failed: {exc}")
    try:
        import claim
        out.extend(f"claim {c['item']} by {c['owner']} expired {c['age_hours']}h ago without release"
                   + (" (corrupt file)" if c.get("corrupt") else "") for c in claim.status() if c.get("expired"))
        out.extend("claim abuse: " + line for line in claim.recent_events())
    except Exception as exc:  # noqa: BLE001
        out.append(f"claim status failed: {exc}")
    try:
        import hashlib
        skill = os.path.join(ROOT, "skills", "diligence", "SKILL.md")
        pin = open(os.path.join(ROOT, "skills", "diligence", "SHA256")).read().split()[0]
        committed = hashlib.sha256(open(skill, "rb").read()).hexdigest()
        if committed != pin:
            out.append("skills/diligence/SKILL.md differs from its pinned SHA256")
        installed = os.path.join(os.environ.get("HERMES_SKILLS_DIR", os.path.expanduser("~/.hermes/skills")),
                                 "research", "diligence", "SKILL.md")
        if not os.path.exists(installed):
            out.append("diligence skill is not installed for this user; run skills/diligence/install.sh")
        elif hashlib.sha256(open(installed, "rb").read()).hexdigest() != committed:
            out.append("installed diligence skill differs from skills/diligence/SKILL.md; re-run install.sh")
    except OSError:
        out.append("skills/diligence/SHA256 or SKILL.md is missing")
    try:
        dlog = os.path.join(ROOT, "ops", "daemons.log")
        cutoff = time.time() - 24 * 3600
        for line in open(dlog):
            stamp = line[:20].strip()
            try:
                when = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
            except ValueError:
                continue
            if when >= cutoff and line[20:].startswith(("ENABLE", "DISABLE")):
                out.append("daemon flag changed: " + line.strip())
    except OSError:
        pass
    return out


def health(now):
    """Read heartbeats, the hosted file and the diligence guards. Return the problems, or nothing."""
    problems = []
    problems.extend(guard_problems())
    heartbeats = {
        "supervisor": (os.path.join(ROOT, "ops", "supervisor_heartbeat"), 300),
        "live": (os.path.join(ROOT, "ops", "live_heartbeat"), 900),
    }
    problems.extend(failed_jobs(now))
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
    sweep_status()
    for job in JOBS:
        if not due(job, now) or already_ran(job, now):
            continue
        if job["name"] == "health":
            result = health(now)
            if result["problems"]:
                result["post"] = post("health: " + "; ".join(result["problems"]))
        else:
            result = run_script(job["script"], job.get("timeout", 600))
        record(job, now, result)
        ran.append(job["name"])
    return {"ran": ran, "minute": now.strftime("%H:%M")}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from daemon_base import run_loop
    run_loop("scheduler", interval_sec=60, cycle=cycle, align=False)
