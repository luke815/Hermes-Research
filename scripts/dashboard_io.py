"""One safe way to write dashboard/data.json. Every writer goes through here.

Six scripts used to read data.json, change one key and write the whole file
back, with no lock. Two of them running in the same minute lost each other's
key, and build_data_json rewrote the file from scratch so every key it does not
own vanished until the owning script ran again.

update_keys() takes an exclusive lock on a sidecar file, re-reads data.json
inside the lock, merges only the caller's keys, stamps meta.as_of[key] and
writes through a temp file and os.replace, so a reader never sees half a file.

Usage:
    from dashboard_io import update_keys
    update_keys(DATA, {"internals": payload})
"""

from __future__ import annotations

import fcntl
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@contextmanager
def locked(path: str):
    """Exclusive lock on <path>.lock. Absolute path, so the lock does not depend on cwd."""
    lock_path = os.path.abspath(str(path)) + ".lock"
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    with open(lock_path, "a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def read(path: str) -> dict:
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}


def clean(value):
    """NaN and inf become null. json.dump writes them as bare NaN, which the browser cannot parse."""
    if isinstance(value, float):
        return value if value == value and value not in (float("inf"), float("-inf")) else None
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    return value


def write_csv_atomic(path: str, frame) -> None:
    """Replace a CSV under the same lock the dashboard writer uses."""
    path = str(path)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    with locked(path):
        frame.to_csv(tmp)
        os.replace(tmp, path)


def write_atomic(path: str, data: dict) -> None:
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w") as handle:
        json.dump(clean(data), handle, separators=(",", ":"), allow_nan=False)
    os.replace(tmp, path)


def update_keys(path: str, updates: dict, stamp: str | None = None) -> dict:
    """Merge updates into data.json under the lock. Returns the merged document.

    Keys not named in updates are left exactly as they were. meta.as_of records
    when each key was last written, so the page can show its age per panel.
    """
    stamp = stamp or now_utc()
    with locked(path):
        data = read(path)
        data.update(updates)
        meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
        as_of = meta.get("as_of") if isinstance(meta.get("as_of"), dict) else {}
        for key in updates:
            if key != "meta":
                as_of[key] = stamp
        meta["as_of"] = as_of
        data["meta"] = meta
        write_atomic(path, data)
    return data


def write_key(path: str, value) -> None:
    """One job's key file under dashboard/keys/, written whole and atomically.

    The assembler merges these into data.json; it should do so with
    update_keys(), so the merge is locked and meta.as_of records each key.
    """
    os.makedirs(os.path.dirname(os.path.abspath(str(path))), exist_ok=True)
    write_atomic(str(path), value)
