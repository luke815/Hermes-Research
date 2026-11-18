"""Results files are written by scripts, never by hand.

write_result() stamps every results JSON with provenance: the committed script
that produced it (and the hash of that script as it ran), its arguments, the
git commit, the inputs it read with their hashes, a hash of the payload itself,
and the time. It also appends a line to ops/results_ledger.jsonl.
verify_result() checks all of that: a file passes only if a committed,
unmodified script under scripts/ or regime_tester/ wrote it, the payload has
not been edited since, and the ledger has the matching line.

A results file that fails is treated as hand-written: scripts/done_check.py
refuses it and the health check lists it.

    from regime_tester.results_io import write_result
    path = write_result("a1_integrity", payload, inputs=["data/panel_xs"])

A unittest cannot call write_result (it is not a script): tests assert, scripts
write. Daemon-maintained files with a fixed name pass path=, e.g.
    write_result("confirmations", rows_payload, inputs=[...], path="results/sweeps/confirmations.json")
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import socket
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")
LEDGER = os.path.join(ROOT, "ops", "results_ledger.jsonl")
HASH_LIMIT = 64 * 1024 * 1024  # bytes per file; larger inputs record size and mtime only
DIR_HASH_BUDGET = 2 * 1024 * 1024 * 1024  # bytes of directory content hashed before switching to listing only
SCRIPT_DIRS = ("scripts/", "regime_tester/")
NAME = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,80}$")


class NotAScript(RuntimeError):
    """Raised when write_result is called from -c, stdin, a REPL, a test runner or a file outside the repo."""


def _git(root, *args):
    try:
        return subprocess.check_output(["git", *args], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, OSError):
        return None


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def payload_sha256(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _describe_input(root, rel):
    path = os.path.join(root, rel)
    if os.path.isdir(path):
        listing, content, budget, partial = hashlib.sha256(), hashlib.sha256(), DIR_HASH_BUDGET, False
        files = size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            dirnames.sort()
            for name in sorted(filenames):
                if name.startswith("."):
                    continue
                full = os.path.join(dirpath, name)
                stat = os.stat(full)
                relname = os.path.relpath(full, path)
                files += 1
                size += stat.st_size
                listing.update(f"{relname}\t{stat.st_size}\t{stat.st_mtime_ns}\n".encode())
                if stat.st_size <= HASH_LIMIT and budget > 0:
                    content.update(_sha256_file(full).encode())
                    budget -= stat.st_size
                else:
                    partial = True
        return {"path": rel, "kind": "dir", "files": files, "bytes": size, "listing_sha256": listing.hexdigest(),
                "content_sha256": content.hexdigest(), "content_partial": partial}
    if os.path.isfile(path):
        stat = os.stat(path)
        out = {"path": rel, "kind": "file", "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns}
        if stat.st_size <= HASH_LIMIT:
            out["sha256"] = _sha256_file(path)
        return out
    return {"path": rel, "kind": "missing"}


def calling_script(root=ROOT, argv0=None):
    """The committed script running right now, relative to root. Raises NotAScript otherwise.

    Reads the interpreter's own argument list (sys.orig_argv) and __main__'s
    file, not sys.argv[0], which any caller can overwrite.
    """
    orig = list(getattr(sys, "orig_argv", sys.argv))
    if argv0 is None:
        main = sys.modules.get("__main__")
        argv0 = getattr(main, "__file__", None)
        flags = orig[1:3]
        if not argv0 or "-c" in flags or "-" in flags:
            raise NotAScript("write_result needs a script file run as python3 scripts/x.py, not -c, stdin or a REPL")
        if "-m" in flags and not os.path.abspath(argv0).startswith(os.path.abspath(root) + os.sep):
            raise NotAScript(f"write_result cannot be called from {orig[1:3]!r}; tests assert, scripts write")
    script = os.path.abspath(argv0)
    if not os.path.isfile(script):
        raise NotAScript(f"write_result cannot find the running script {script}")
    rel = os.path.relpath(script, root).replace(os.sep, "/")
    if rel.startswith("..") or not rel.startswith(SCRIPT_DIRS) or not rel.endswith(".py"):
        raise NotAScript(f"write_result needs a .py file under scripts/ or regime_tester/, not {rel}")
    return rel


def provenance(root=ROOT, inputs=(), argv0=None, payload=None):
    script = calling_script(root, argv0)
    commit = _git(root, "rev-parse", "HEAD")
    tracked = _git(root, "ls-files", "--error-unmatch", script) is not None
    dirty = bool(_git(root, "status", "--porcelain", "--", script))
    return {
        "script": script,
        "script_blob": _git(root, "hash-object", script),
        "script_tracked": tracked,
        "script_dirty": dirty,
        "argv": [str(a) for a in sys.argv[1:]],
        "orig_argv": [str(a) for a in getattr(sys, "orig_argv", sys.argv)],
        "commit": commit,
        "written_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "host": socket.gethostname(),
        "python": platform.python_version(),
        "inputs": [_describe_input(root, str(i)) for i in inputs],
        "payload_sha256": payload_sha256(payload if payload is not None else {}),
    }


def _ledger_path(root):
    return os.path.join(root, "ops", "results_ledger.jsonl")


def write_result(name, payload, *, inputs=(), date=None, path=None, root=ROOT, argv0=None):
    """Write a provenance-stamped results JSON and record it in the ledger. Returns the path.

    name: the item or test, e.g. "a1_integrity"; the file is results/<date>_<name>.json.
    inputs: paths relative to root that the script read; at least one is required.
    path: a fixed location under results/ or ops/ for files a daemon maintains.
    argv0 is for tools that write on behalf of a script (data_guard); scripts leave it alone.
    """
    if not isinstance(payload, dict):
        raise TypeError("payload must be a dict")
    if "provenance" in payload:
        raise ValueError("payload must not carry its own provenance; write_result adds it")
    if not inputs:
        raise ValueError("inputs=[...] must name the data the script read, so the file says what it describes")
    if not NAME.match(name):
        raise ValueError(f"name {name!r} must be lowercase letters, digits, _ . -")
    stamp = provenance(root, inputs, argv0, payload)
    if path:
        rel = path.replace(os.sep, "/").lstrip("/")
        if not rel.startswith(("results/", "ops/")) or ".." in rel or not rel.endswith(".json"):
            raise ValueError("path must be a .json under results/ or ops/")
        out = os.path.join(root, rel)
    else:
        day = date or stamp["written_at"][:10]
        out = os.path.join(root, "results", f"{day}_{name}.json")
        rel = os.path.relpath(out, root)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    body = dict(payload)
    body["provenance"] = stamp
    tmp = f"{out}.{os.getpid()}.tmp"
    with open(tmp, "w") as handle:
        json.dump(body, handle, indent=1, allow_nan=False)
    os.replace(tmp, out)
    ledger = _ledger_path(root)
    os.makedirs(os.path.dirname(ledger), exist_ok=True)
    with open(ledger, "a") as handle:
        handle.write(json.dumps({"path": rel, "payload_sha256": stamp["payload_sha256"], "commit": stamp["commit"],
                                 "script": stamp["script"], "written_at": stamp["written_at"]}) + "\n")
    return out


def _in_ledger(root, rel, digest):
    ledger = _ledger_path(root)
    if not os.path.exists(ledger):
        return False
    with open(ledger) as handle:
        for line in handle:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("path") == rel and row.get("payload_sha256") == digest:
                return True
    return False


def verify_result(path, root=ROOT):
    """Problems with a results file's provenance. An empty list means it passes."""
    try:
        with open(path) as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"unreadable: {exc}"]
    stamp = data.get("provenance") if isinstance(data, dict) else None
    if not isinstance(stamp, dict):
        return ["no provenance stamp: written by hand or by an unstamped script"]
    problems = []
    script, commit = stamp.get("script"), stamp.get("commit")
    if not isinstance(script, str) or not script.endswith(".py") or not script.startswith(SCRIPT_DIRS):
        problems.append(f"script {script!r} is not a .py file under scripts/ or regime_tester/")
        script = None
    if not commit or _git(root, "merge-base", "--is-ancestor", str(commit), "HEAD") is None:
        problems.append(f"commit {commit!r} is not in this repository's history")
    elif script:
        committed_blob = _git(root, "rev-parse", f"{commit}:{script}")
        if committed_blob is None:
            problems.append(f"script {script} was not committed at {commit}; commit the script before writing results")
        elif stamp.get("script_blob") != committed_blob:
            problems.append(f"script {script} as run differs from the version committed at {commit} (edited, run, reverted)")
    if stamp.get("script_dirty") or stamp.get("script_tracked") is False:
        problems.append(f"script {script or '?'} was modified or untracked when it ran")
    payload = {k: v for k, v in data.items() if k != "provenance"}
    digest = payload_sha256(payload)
    if stamp.get("payload_sha256") != digest:
        problems.append("payload edited after it was written")
    if not stamp.get("inputs"):
        problems.append("no inputs declared; a results file names the data it read")
    rel = os.path.relpath(os.path.abspath(path), root).replace(os.sep, "/")
    if not _in_ledger(root, rel, digest):
        problems.append("no matching line in ops/results_ledger.jsonl")
    return problems


def main(argv):
    """python3 -m regime_tester.results_io verify results/<file>.json [...]"""
    if len(argv) < 3 or argv[1] != "verify":
        print(main.__doc__)
        return 2
    bad = 0
    for path in argv[2:]:
        problems = verify_result(path)
        print(("OK   " if not problems else "FAIL ") + path + ("" if not problems else ": " + "; ".join(problems)))
        bad += bool(problems)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
