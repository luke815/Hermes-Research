"""daemon_base.run_loop: every daemon on this box runs through this.

    from daemon_base import run_loop
    def cycle(ctx):            # do one unit of work and return a dict for the heartbeat
        ...
        return {"calls": 5, "pushed": True, "as_of": "..."}
    if __name__ == "__main__":
        run_loop("live", interval_sec=300, cycle=cycle, align=True, offset_sec=20)

Guarantees:
  - Single instance: an exclusive flock on ops/locks/NAME.lock; a second copy exits at once with a message.
  - Heartbeat ops/NAME_heartbeat is JSON with ts, ts_epoch, phase (starting|working|idle|error),
    cycles, last_error, version (git short hash at start), and whatever the cycle returned.
  - The first cycle runs immediately. Sleep comes after work, never before.
  - With align=True the loop wakes at the next multiple of interval_sec after the epoch, plus offset_sec,
    so a 5-minute daemon fires at :00:20, :05:20, ... regardless of how long the last cycle took.
    Sleep is capped at interval_sec, so a clock jump or a long cycle cannot stall the loop.
  - An exception inside a cycle is logged with a traceback, written to the heartbeat as last_error,
    and the loop continues. Nothing inside a cycle can kill the daemon except SIGTERM/SIGINT.
  - Per-cycle budget: if a cycle runs longer than max_cycle_sec it is reported in the heartbeat
    (phase stays "working" with a started_at), so a hung pull is visible from the outside.
  - SIGTERM ends the loop after the current cycle; the heartbeat records phase "stopped".
"""
import fcntl, json, os, signal, subprocess, sys, time, traceback

_STOP = False


def _head():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _write_hb(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, path)


def _log(msg):
    sys.stdout.write(time.strftime("%Y-%m-%dT%H:%M:%SZ ", time.gmtime()) + msg + "\n")
    sys.stdout.flush()


def run_loop(name, interval_sec, cycle, align=True, offset_sec=0, max_cycle_sec=None):
    global _STOP
    os.makedirs("ops/locks", exist_ok=True)
    lock_fd = os.open(f"ops/locks/{name}.lock", os.O_RDWR | os.O_CREAT)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        _log(f"{name}: another instance holds the lock, exiting")
        sys.exit(0)
    hb_path = f"ops/{name}_heartbeat"
    version = _head()
    max_cycle_sec = max_cycle_sec or interval_sec

    def on_sig(signum, frame):
        global _STOP
        _STOP = True
        _log(f"{name}: signal {signum}, stopping after this cycle")
    signal.signal(signal.SIGTERM, on_sig)
    signal.signal(signal.SIGINT, on_sig)

    state = {"name": name, "phase": "starting", "cycles": 0, "last_error": None, "version": version,
             "interval_sec": interval_sec, "pid": os.getpid()}

    def hb(**extra):
        now = time.time()
        state.update(extra)
        state["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
        state["ts_epoch"] = int(now)
        _write_hb(hb_path, state)

    hb()
    _log(f"{name}: started pid {os.getpid()} version {version} interval {interval_sec}s")
    ctx = {"name": name, "version": version}
    while not _STOP:
        started = time.time()
        hb(phase="working", started_at=int(started))
        try:
            result = cycle(ctx) or {}
            state["cycles"] += 1
            state["last_error"] = None
            hb(phase="idle", cycle_sec=round(time.time() - started, 1), **{k: v for k, v in result.items() if k not in state or k in ("as_of", "calls", "pushed")})
            _log(f"{name}: cycle {state['cycles']} ok in {time.time() - started:.1f}s {json.dumps(result)[:300]}")
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            _log(f"{name}: cycle error {err}\n" + traceback.format_exc())
            hb(phase="error", last_error=err[:300], cycle_sec=round(time.time() - started, 1))
        if time.time() - started > max_cycle_sec:
            _log(f"{name}: cycle took {time.time() - started:.0f}s, over the {max_cycle_sec}s budget")
        if _STOP:
            break
        now = time.time()
        if align:
            nxt = (int(now) // interval_sec + 1) * interval_sec + offset_sec
            sleep_for = max(1, min(interval_sec, nxt - now))
        else:
            sleep_for = max(1, min(interval_sec, interval_sec - (now - started)))
        # sleep in short slices so SIGTERM is honoured promptly
        end = time.time() + sleep_for
        while not _STOP and time.time() < end:
            time.sleep(min(5, max(0.1, end - time.time())))
    hb(phase="stopped")
    _log(f"{name}: stopped after {state['cycles']} cycles")
