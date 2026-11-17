"""Merge every key file over the daily base and write data.json.

Each job writes only its own key to dashboard/keys/<key>.json. This is the only
script that writes or pushes data.json, so one job can no longer erase another's
key by rebuilding the whole file.
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "dashboard", "data.json")
KEYS = os.path.join(ROOT, "dashboard", "keys")


def assemble():
    """Merge through the locked writer, so meta.as_of records each panel."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import dashboard_io
    updates = {}
    for name in sorted(os.listdir(KEYS)):
        if name.endswith(".json"):
            updates[name[:-5]] = json.load(open(os.path.join(KEYS, name)))
    dashboard_io.update_keys(BASE, updates)
    return sorted(updates)


if __name__ == "__main__":
    print("keys", assemble())
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from push import push
    print(push("dashboard"))
