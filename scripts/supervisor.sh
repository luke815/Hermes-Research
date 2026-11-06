#!/bin/bash
# Supervisor for the long-running daemons. Started once, detached, and it
# outlives the session that launched it. Every 30 seconds it restarts a daemon
# whose process is gone. It never starts a second copy of one that is running.
#
# Start: setsid nohup bash scripts/supervisor.sh >/dev/null 2>&1 < /dev/null &
# The hourly job checks ops/supervisor_heartbeat and restarts this script, not
# the daemons.

ROOT=/opt/data/workspace/regime-tester
PY=/opt/hermes/.venv/bin/python3
HEARTBEAT=$ROOT/ops/supervisor_heartbeat

ensure() {
    name=$1
    if pgrep -f "scripts/${name}.py" >/dev/null; then
        return
    fi
    cd "$ROOT" && PYTHONPATH=/opt/data/.local/lib/python3.14/site-packages \
        "$PY" "scripts/${name}.py" >> "$ROOT/ops/${name}.log" 2>&1 &
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) restarted ${name} pid $!" >> "$ROOT/ops/supervisor.log"
}

while true; do
    ensure live_daemon
    ensure sweep_daemon
    tmp=${HEARTBEAT}.tmp
    date -u +%Y-%m-%dT%H:%M:%SZ > "$tmp"
    mv -f "$tmp" "$HEARTBEAT"
    sleep 30
done
