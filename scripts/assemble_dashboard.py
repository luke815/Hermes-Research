"""Merge every key file over the daily base and write data.json.

Each job writes only its own key to dashboard/keys/<key>.json. This is the only
script that writes or pushes data.json, so one job can no longer erase another's
key by rebuilding the whole file.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "dashboard", "data.json")
KEYS = os.path.join(ROOT, "dashboard", "keys")


def assemble():
    """Stamp each key with its file's modification time, not the assembly time.

    A stale key file would otherwise look fresh because the stamp is when the
    assembler ran, not when the job wrote it.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import dashboard_io
    merged = []
    for name in sorted(os.listdir(KEYS)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(KEYS, name)
        stamp = datetime.fromtimestamp(os.path.getmtime(path), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        dashboard_io.update_keys(BASE, {name[:-5]: json.load(open(path))}, stamp=stamp)
        merged.append(name[:-5])
    return merged


if __name__ == "__main__":
    print("keys", assemble())
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from push import push
    print(push("dashboard"))
