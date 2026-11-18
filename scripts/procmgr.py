#!/usr/bin/env python3
"""procmgr: the only way daemons are started, stopped and checked on this box.

Usage (run from the workspace root, e.g. /opt/data/workspace/regime-tester):
  python3 scripts/procmgr.py start NAME -- <command...>   start NAME detached (no-op if alive)
  python3 scripts/procmgr.py stop NAME                    SIGTERM, wait 20s, SIGKILL
  python3 scripts/procmgr.py restart NAME                 stop, then start with the registered command
  python3 scripts/procmgr.py status [NAME]                pid, alive, uptime, heartbeat age, version
  python3 scripts/procmgr.py supervise                    start every registered daemon that is not alive
  python3 scripts/procmgr.py register NAME -- <command...> register without starting
  python3 scripts/procmgr.py disable NAME REASON          stop NAME and keep it off: start, restart and supervise refuse it,
                                                          and so does the same command under another name
  python3 scripts/procmgr.py enable NAME REASON           remove the disabled flag (does not start it)
  Both are appended to ops/daemons.log, which the health check reads.

Rules this enforces:
  - Identity is a pidfile (ops/pids/NAME.pid) plus a lock (ops/locks/NAME.lock), never a process name.
  - start double-forks and setsids, so the child's parent is init and it outlives the tool call.
  - stdout/stderr go to ops/logs/NAME.log, unbuffered.
  - The registry (ops/daemons.json) remembers each NAME's command, so supervise and restart need no arguments.
  - status reports the git hash the process started from (ops/pids/NAME.version) next to HEAD, so a
    daemon running stale code is visible.
"""
import fcntl, json, os, signal, subprocess, sys, time

ROOT = os.getcwd()
OPS = os.path.join(ROOT, "ops")
REG = os.path.join(OPS, "daemons.json")
DLOG = os.path.join(OPS, "daemons.log")


def _dirs():
    for sub in ("pids", "locks", "logs", "disabled"):
        os.makedirs(os.path.join(OPS, sub), exist_ok=True)


def _dlog(line):
    _dirs()
    with open(DLOG, "a") as f:
        f.write(time.strftime("%Y-%m-%dT%H:%M:%SZ ", time.gmtime()) + line + "\n")


def _reg():
    try:
        return json.load(open(REG))
    except Exception:
        return {}


def _save_reg(r):
    _dirs()
    tmp = REG + ".tmp"
    json.dump(r, open(tmp, "w"), indent=1)
    os.replace(tmp, REG)


def _pidfile(n): return os.path.join(OPS, "pids", f"{n}.pid")
def _lockfile(n): return os.path.join(OPS, "locks", f"{n}.lock")
def _verfile(n): return os.path.join(OPS, "pids", f"{n}.version")
def _logfile(n): return os.path.join(OPS, "logs", f"{n}.log")
def _hbfile(n): return os.path.join(OPS, f"{n}_heartbeat")
def _disabledfile(n): return os.path.join(OPS, "disabled", f"{n}")


def _disabled():
    """{name: flag} for every disabled daemon."""
    out = {}
    folder = os.path.join(OPS, "disabled")
    if not os.path.isdir(folder):
        return out
    for name in os.listdir(folder):
        try:
            out[name] = json.load(open(os.path.join(folder, name)))
        except Exception:
            out[name] = {"name": name, "reason": "unreadable flag"}
    return out


def _same_cmd(a, b):
    """Two commands are the same daemon if they run the same script file."""
    def key(cmd):
        for part in cmd or []:
            if str(part).endswith(".py"):
                return os.path.realpath(os.path.join(ROOT, part))
        return tuple(cmd or [])
    return bool(a) and bool(b) and key(a) == key(b)


def is_disabled(n, cmd=None):
    """A disabled daemon stays off until enable: stop alone is undone by the supervisor within 60s.

    The flag covers the name and the command, so the same script under a new name is refused too.
    """
    flags = _disabled()
    if n in flags:
        return True
    return any(_same_cmd(cmd or _reg().get(n, {}).get("cmd"), flag.get("cmd")) for flag in flags.values())


def _disabled_reason(n):
    for name, flag in _disabled().items():
        if name == n or _same_cmd(_reg().get(n, {}).get("cmd"), flag.get("cmd")):
            return f"{flag.get('reason', '')} (flag {name})"
    return ""


def disable(n, reason=""):
    if len(reason.strip()) < 10:
        print("disable needs a reason, e.g. 'review: off until A2 two-cell test passes'"); return 2
    _dirs()
    with open(_disabledfile(n), "w") as f:
        json.dump({"name": n, "cmd": _reg().get(n, {}).get("cmd"), "reason": reason,
                   "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, f)
    if _alive(_pid(n)):
        stop(n)
    _dlog(f"DISABLE {n}: {reason}")
    print(f"{n}: disabled ({reason}); start, restart and supervise will refuse it until enable")
    return 0


def enable(n, reason=""):
    if len(reason.strip()) < 10:
        print("enable needs a reason, e.g. 'A2 two-cell test passed in 1a2b3c4'"); return 2
    try:
        os.remove(_disabledfile(n))
        _dlog(f"ENABLE {n}: {reason}")
        print(f"{n}: enabled (not started; use start or wait for supervise)")
    except FileNotFoundError:
        print(f"{n}: was not disabled")
    return 0


def _head():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unknown"


def _pid(n):
    try:
        return int(open(_pidfile(n)).read().strip())
    except Exception:
        return None


def _alive(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:  # zombie check
        with open(f"/proc/{pid}/stat") as f:
            if f.read().split(")")[-1].split()[0] == "Z":
                return False
    except Exception:
        pass
    return True


def _lock_held(n):
    """True if some process holds NAME's lock (the daemon acquires it in daemon_base.run_loop)."""
    _dirs()
    fd = os.open(_lockfile(n), os.O_RDWR | os.O_CREAT)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    except OSError:
        return True
    finally:
        os.close(fd)


def is_running(n):
    return _alive(_pid(n)) or _lock_held(n)


def start(n, cmd):
    if not cmd:
        cmd = _reg().get(n, {}).get("cmd")
    if not cmd:
        print(f"{n}: no command given and none registered"); return 2
    if is_disabled(n, cmd):
        print(f"{n}: disabled, not started ({_disabled_reason(n) or 'same command as a disabled daemon'}); "
              f"run procmgr.py enable <name> <reason> first"); return 3
    _dirs()
    r = _reg(); r[n] = {"cmd": cmd}; _save_reg(r)
    if is_running(n):
        print(f"{n}: already running (pid {_pid(n)})"); return 0
    log = open(_logfile(n), "ab", buffering=0)
    pid = os.fork()
    if pid == 0:  # child
        os.setsid()
        if os.fork() != 0:
            os._exit(0)  # first child exits; grandchild is orphaned to init
        os.chdir(ROOT)
        os.umask(0o022)
        devnull = os.open(os.devnull, os.O_RDONLY)
        os.dup2(devnull, 0); os.dup2(log.fileno(), 1); os.dup2(log.fileno(), 2)
        with open(_pidfile(n), "w") as f:
            f.write(str(os.getpid()))
        with open(_verfile(n), "w") as f:
            f.write(_head())
        env = dict(os.environ, PYTHONUNBUFFERED="1", DAEMON_NAME=n)
        try:
            os.execvpe(cmd[0], cmd, env)
        except Exception as e:  # pragma: no cover
            os.write(2, f"exec failed: {e}\n".encode()); os._exit(127)
    os.waitpid(pid, 0)  # reap the first child
    time.sleep(0.5)
    p = _pid(n)
    print(f"{n}: started pid {p} (parent {_ppid(p)}), log {_logfile(n)}, version {_head()}")
    return 0 if _alive(p) else 1


def _ppid(pid):
    try:
        with open(f"/proc/{pid}/stat") as f:
            return int(f.read().split(")")[-1].split()[1])
    except Exception:
        return None


def stop(n, timeout=20):
    pid = _pid(n)
    if not _alive(pid):
        print(f"{n}: not running"); return 0
    try:
        os.killpg(os.getpgid(pid), signal.SIGTERM)
    except Exception:
        os.kill(pid, signal.SIGTERM)
    t0 = time.time()
    while _alive(pid) and time.time() - t0 < timeout:
        time.sleep(0.5)
    if _alive(pid):
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except Exception:
            os.kill(pid, signal.SIGKILL)
        time.sleep(0.5)
    print(f"{n}: stopped (pid {pid}, {'killed' if time.time() - t0 >= timeout else 'terminated'})")
    return 0


def status(names=None):
    r = _reg()
    names = names or sorted(r.keys())
    head = _head()
    out = []
    for n in names:
        pid = _pid(n); alive = _alive(pid)
        up = None
        if alive:
            try:
                up = int(time.time() - os.stat(f"/proc/{pid}").st_ctime)
            except Exception:
                pass
        hb_age, hb = None, {}
        try:
            hb = json.load(open(_hbfile(n)))
            hb_age = int(time.time() - hb.get("ts_epoch", 0))
        except Exception:
            pass
        try:
            ver = open(_verfile(n)).read().strip()
        except Exception:
            ver = "?"
        row = {"name": n, "pid": pid, "alive": alive, "uptime_s": up, "heartbeat_age_s": hb_age,
               "phase": hb.get("phase"), "cycles": hb.get("cycles"), "last_error": hb.get("last_error"),
               "version": ver, "head": head, "stale_code": alive and ver not in ("?", head),
               "disabled": is_disabled(n)}
        out.append(row)
        print(json.dumps(row))
    return out


def supervise():
    r = _reg(); started = []; skipped = []
    for n, spec in r.items():
        if is_disabled(n):
            skipped.append(n); continue
        if not is_running(n):
            start(n, spec["cmd"]); started.append(n)
    with open(os.path.join(OPS, "supervisor_heartbeat"), "w") as f:
        json.dump({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "ts_epoch": int(time.time()),
                   "checked": list(r.keys()), "started": started}, f)
    print(f"supervise: checked {len(r)}, started {started}, skipped disabled {skipped}")
    return 0


def main(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    op = argv[1]
    if op in ("start", "register"):
        n = argv[2]; cmd = argv[argv.index("--") + 1:] if "--" in argv else None
        if op == "register":
            r = _reg(); r[n] = {"cmd": cmd}; _save_reg(r); print(f"{n}: registered {cmd}"); return 0
        return start(n, cmd)
    if op == "stop":
        return stop(argv[2])
    if op == "restart":
        if is_disabled(argv[2]):
            print(f"{argv[2]}: disabled ({_disabled_reason(argv[2])}); not restarted"); return 3
        stop(argv[2]); return start(argv[2], None)
    if op == "status":
        status(argv[2:3] or None); return 0
    if op == "supervise":
        return supervise()
    if op == "disable" and len(argv) >= 3:
        return disable(argv[2], " ".join(argv[3:]))
    if op == "enable" and len(argv) >= 3:
        return enable(argv[2], " ".join(argv[3:]))
    print(__doc__); return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
