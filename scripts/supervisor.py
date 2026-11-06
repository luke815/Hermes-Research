"""The supervisor is itself a daemon: every 60 seconds, start whatever registered daemon is not alive.
Start it once with:  python3 scripts/procmgr.py start supervisor -- python3 scripts/supervisor.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from daemon_base import run_loop
import procmgr


def cycle(ctx):
    reg = procmgr._reg()
    started = []
    for name, spec in reg.items():
        if name == "supervisor":
            continue
        if not procmgr.is_running(name):
            procmgr.start(name, spec["cmd"]); started.append(name)
    return {"checked": len(reg) - 1, "started": started}


if __name__ == "__main__":
    run_loop("supervisor", interval_sec=60, cycle=cycle, align=False)
