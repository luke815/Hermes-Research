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
    data = json.load(open(BASE))
    if os.path.isdir(KEYS):
        for name in sorted(os.listdir(KEYS)):
            if name.endswith(".json"):
                key = name[:-5]
                data[key] = json.load(open(os.path.join(KEYS, name)))
    tmp = BASE + ".tmp"
    json.dump(data, open(tmp, "w"))
    os.replace(tmp, BASE)
    return sorted(k for k in data if k not in ("series",))


if __name__ == "__main__":
    print("keys", assemble())
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from push import push
    print(push("dashboard"))
