"""Data directories change only through a swap, never by hand.

On 2026-11-17, 842 files were deleted from data/panel_xs by hand, with no
script and no backup. Nothing could restore them. This tool gives every data
directory a manifest (every file, its size and content hash), reports any file
that vanished, shrank or was rewritten since the last manifest, and replaces a
directory only by moving the old one aside.

    python3 scripts/data_guard.py snapshot data/panel_xs
        record the directory in ops/manifests/. Refuses if files vanished,
        shrank or were rewritten since the last manifest, unless you pass
        --accept-removed N --accept-shrunk N --accept-changed N with --reason
        "<item>: what was lost and why" (the counts must match exactly).

    python3 scripts/data_guard.py check data/panel_xs
        list files removed, shrunk or rewritten in place since the last
        manifest; exit 1 if any. Files that grew (a puller appended) are fine.

    python3 scripts/data_guard.py record-write data/panel_xs --reason "funding_sum_daemon: 40 names" a.csv b.csv
        a registered writer declares the files it rewrote; only those manifest entries are
        refreshed, so the next check does not read a narrower or re-sorted file as a loss.

    python3 scripts/data_guard.py swap --src data/panel_xs_new --dst data/panel_xs \\
        --reason "A1: sorted, funded, future bars dropped" [--allow-removed N] [--allow-shrunk N]
        compare the two, refuse if files would disappear or shrink unless the
        counts are passed exactly, move dst to dst.prev-<stamp>, rename src to
        dst, write a provenance-stamped results file and a new manifest.

Nothing here deletes a file. The .prev directories are the backup; remove them
by hand only after the next day's run has read the new directory without
complaint. Every snapshot and swap is a line in ops/manifests/changes.jsonl,
and the health check posts any line from the last 24 hours that lost data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from regime_tester.results_io import write_result  # noqa: E402

MANIFESTS = os.path.join(ROOT, "ops", "manifests")
HASH_LIMIT = 64 * 1024 * 1024
ITEM_IN_REASON = re.compile(r"\b[A-Z]{1,3}\d{1,3}[a-z]?\b")


def _stamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _manifest_path(rel, manifests=MANIFESTS):
    return os.path.join(manifests, rel.strip("/").replace("/", "__") + ".json")


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan(path):
    """{relative file path: {bytes, mtime, sha256}} for every regular file under path."""
    out = {}
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames.sort()
        for name in sorted(filenames):
            if name.startswith("."):
                continue
            full = os.path.join(dirpath, name)
            if not os.path.isfile(full):
                continue
            stat = os.stat(full)
            rel = os.path.relpath(full, path).replace(os.sep, "/")
            entry = {"bytes": stat.st_size, "mtime": int(stat.st_mtime)}
            if stat.st_size <= HASH_LIMIT:
                entry["sha256"] = _sha256(full)
            out[rel] = entry
    return out


def compare(before, after):
    """Differences between two manifests' entries. 'rewritten' is a changed file that did not grow."""
    both = set(before) & set(after)
    fingerprint = lambda e: e.get("sha256") or f"mtime:{e.get('mtime')}"  # noqa: E731
    return {
        "removed": sorted(set(before) - set(after)),
        "added": sorted(set(after) - set(before)),
        "shrunk": sorted(n for n in both if after[n]["bytes"] < before[n]["bytes"]),
        "rewritten": sorted(n for n in both if after[n]["bytes"] <= before[n]["bytes"]
                            and fingerprint(after[n]) != fingerprint(before[n])),
        "before_files": len(before), "after_files": len(after),
    }


def _load_manifest(rel, manifests):
    out = _manifest_path(rel, manifests)
    if not os.path.exists(out):
        return None
    with open(out) as handle:
        return json.load(handle)


def _append_change(manifests, record):
    os.makedirs(manifests, exist_ok=True)
    with open(os.path.join(manifests, "changes.jsonl"), "a") as handle:
        handle.write(json.dumps({"at": _stamp(), **record}) + "\n")


def _need_reason(reason, what):
    if len((reason or "").strip()) < 10 or not ITEM_IN_REASON.search(reason or ""):
        raise SystemExit(f"--reason must name the backlog item (e.g. A1) and say {what}")


def snapshot(rel, root=ROOT, manifests=MANIFESTS, note="", accept_removed=0, accept_shrunk=0, accept_changed=0):
    """Record the directory. Refuses to paper over a loss unless the loss is declared exactly."""
    path = os.path.join(root, rel)
    if not os.path.isdir(path):
        raise SystemExit(f"{rel} is not a directory under the repository")
    files = scan(path)
    previous = _load_manifest(rel, manifests)
    diff = None
    if previous is not None:
        diff = compare(previous["entries"], files)
        counts = (len(diff["removed"]), len(diff["shrunk"]), len(diff["rewritten"]))
        if counts != (int(accept_removed), int(accept_shrunk), int(accept_changed)):
            raise SystemExit(f"refusing: since the last manifest of {rel}, {counts[0]} files were removed, {counts[1]} shrank, "
                             f"{counts[2]} were rewritten. Data changes go through swap. To record a loss, pass "
                             f"--accept-removed {counts[0]} --accept-shrunk {counts[1]} --accept-changed {counts[2]} "
                             f"--reason '<item>: what was lost and why'")
        if any(counts):
            _need_reason(note, "what was lost and why")
        out = _manifest_path(rel, manifests)
        shutil.copy(out, f"{out}.{_stamp().replace(':', '')}.prev")  # manifests keep their history
    record = {"dir": rel, "taken_at": _stamp(), "files": len(files), "bytes": sum(f["bytes"] for f in files.values()),
              "note": note, "entries": files}
    os.makedirs(manifests, exist_ok=True)
    out = _manifest_path(rel, manifests)
    tmp = f"{out}.{os.getpid()}.tmp"
    with open(tmp, "w") as handle:
        json.dump(record, handle)
    os.replace(tmp, out)
    _append_change(manifests, {"op": "snapshot", "dir": rel, "files": len(files),
                               "removed": int(accept_removed), "shrunk": int(accept_shrunk),
                               "rewritten": int(accept_changed), "reason": note})
    return record


def check(rel, root=ROOT, manifests=MANIFESTS):
    """Problems since the last manifest. Empty list means nothing vanished, shrank or was rewritten."""
    previous = _load_manifest(rel, manifests)
    if previous is None:
        return [f"{rel}: no manifest; run data_guard.py snapshot {rel} and say why in the report"]
    path = os.path.join(root, rel)
    if not os.path.isdir(path):
        return [f"{rel}: directory is missing"]
    diff = compare(previous["entries"], scan(path))
    problems = []
    for key, verb in (("removed", "removed"), ("shrunk", "shrank"), ("rewritten", "were rewritten in place")):
        if diff[key]:
            problems.append(f"{rel}: {len(diff[key])} files {verb} since the last manifest, e.g. " + ", ".join(diff[key][:5]))
    return problems


def record_write(rel, files, reason, root=ROOT, manifests=MANIFESTS):
    """A registered writer declares the files it just wrote, so the next check does not read them as a loss.

    Daily pullers rewrite panel files in place (sorted, re-funded), and a narrower funding
    column makes a file smaller. Those are not hand edits. The writer calls this right after
    its batch, naming the files and itself; only those manifest entries are refreshed, and the
    write is logged. Files the writer did not name stay as they were, so a deletion elsewhere
    in the directory is still caught.

        from data_guard import record_write
        record_write("data/panel_xs", written_names, "pull_listed_history: 25 names refreshed")
    """
    if len((reason or "").strip()) < 10:
        raise SystemExit("record_write needs a reason naming the writer and what it wrote")
    previous = _load_manifest(rel, manifests)
    if previous is None:
        raise SystemExit(f"{rel}: no manifest; run data_guard.py snapshot {rel} first")
    path = os.path.join(root, rel)
    entries = previous["entries"]
    shrunk = rewritten = grown = added = 0
    for name in files:
        name = str(name).replace(os.sep, "/")
        full = os.path.join(path, name)
        if not os.path.isfile(full):
            raise SystemExit(f"record_write: {name} is not a file under {rel}; a writer may not declare a deletion")
        stat = os.stat(full)
        entry = {"bytes": stat.st_size, "mtime": int(stat.st_mtime)}
        if stat.st_size <= HASH_LIMIT:
            entry["sha256"] = _sha256(full)
        before = entries.get(name)
        if before is None:
            added += 1
        elif entry["bytes"] < before["bytes"]:
            shrunk += 1
        elif entry["bytes"] > before["bytes"]:
            grown += 1
        elif entry.get("sha256") != before.get("sha256"):
            rewritten += 1
        entries[name] = entry
    previous["entries"] = entries
    previous["files"] = len(entries)
    previous["bytes"] = sum(e["bytes"] for e in entries.values())
    previous["note"] = f"record_write: {reason}"
    out = _manifest_path(rel, manifests)
    tmp = f"{out}.{os.getpid()}.tmp"
    with open(tmp, "w") as handle:
        json.dump(previous, handle)
    os.replace(tmp, out)
    counts = {"declared": len(files), "added": added, "grown": grown, "shrunk": shrunk, "rewritten": rewritten}
    _append_change(manifests, {"op": "record_write", "dir": rel, "reason": reason, **counts})
    return counts


def recent_losses(manifests=MANIFESTS, hours=24, now=None):
    """changes.jsonl lines from the last `hours` that recorded removed, shrunk or rewritten files."""
    path = os.path.join(manifests, "changes.jsonl")
    if not os.path.exists(path):
        return []
    cutoff = (now or datetime.now(timezone.utc)).timestamp() - hours * 3600
    out = []
    with open(path) as handle:
        for line in handle:
            try:
                row = json.loads(line)
                when = datetime.strptime(row["at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
            except (ValueError, KeyError, TypeError):
                continue
            if row.get("op") == "record_write":
                continue  # a declared write by a registered writer is not a loss
            if when >= cutoff and any(row.get(k) for k in ("removed", "shrunk", "rewritten")):
                out.append(f"{row['at']} {row.get('op')} {row.get('dir')}: removed {row.get('removed', 0)}, "
                           f"shrunk {row.get('shrunk', 0)}, rewritten {row.get('rewritten', 0)}; {row.get('reason', '')}")
    return out


def swap(src, dst, reason, allow_removed=0, allow_shrunk=0, root=ROOT, manifests=MANIFESTS, argv0=None):
    """Replace dst with src, keeping dst as dst.prev-<stamp>. Returns the record written."""
    src_path, dst_path = os.path.join(root, src), os.path.join(root, dst)
    if not os.path.isdir(src_path):
        raise SystemExit(f"source {src} is not a directory")
    a, b = os.path.realpath(src_path), os.path.realpath(dst_path)
    if a == b or os.path.commonpath([a, b]) in (a, b):
        raise SystemExit("source and destination must be sibling directories, not the same or nested")
    _need_reason(reason, "what changed")
    before = scan(dst_path) if os.path.isdir(dst_path) else {}
    after = scan(src_path)
    if not after:
        raise SystemExit(f"refusing: source {src} is empty")
    diff = compare(before, after)
    if len(diff["removed"]) != int(allow_removed) or len(diff["shrunk"]) != int(allow_shrunk):
        raise SystemExit(f"refusing: {len(diff['removed'])} files in {dst} are not in {src} and {len(diff['shrunk'])} would shrink "
                         f"(--allow-removed {allow_removed} --allow-shrunk {allow_shrunk}). First removed: {diff['removed'][:10]}. "
                         "Rebuild them into the source directory, or pass the exact counts with a reason that says why.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    incoming = f"{dst_path}.incoming-{stamp}"
    prev = f"{dst}.prev-{stamp}" if os.path.isdir(dst_path) else None
    os.rename(src_path, incoming)
    try:
        if prev:
            os.rename(dst_path, os.path.join(root, prev))
        os.rename(incoming, dst_path)
    except OSError:
        if prev and not os.path.isdir(dst_path) and os.path.isdir(os.path.join(root, prev)):
            os.rename(os.path.join(root, prev), dst_path)
        if os.path.isdir(incoming):
            os.rename(incoming, src_path)
        raise
    record = {"swap": {"src": src, "dst": dst, "kept_previous_as": prev, "reason": reason},
              "diff": {k: (v if isinstance(v, int) else v[:200]) for k, v in diff.items()},
              "diff_counts": {k: len(v) for k, v in diff.items() if isinstance(v, list)}}
    path = write_result(f"swap_{dst.strip('/').replace('/', '__')}", record, inputs=[dst] + ([prev] if prev else []),
                        root=root, argv0=argv0 or __file__)
    record["results_file"] = os.path.relpath(path, root)
    # the new directory is the baseline; declared losses are those the swap just accepted
    previous = _load_manifest(dst, manifests)
    if previous is not None:
        d2 = compare(previous["entries"], scan(dst_path))
        snapshot(dst, root, manifests, note=f"after swap: {reason}", accept_removed=len(d2["removed"]),
                 accept_shrunk=len(d2["shrunk"]), accept_changed=len(d2["rewritten"]))
    else:
        snapshot(dst, root, manifests, note=f"after swap: {reason}")
    _append_change(manifests, {"op": "swap", "dir": dst, **record["swap"], **{k: record["diff_counts"][k] for k in ("removed", "shrunk", "rewritten", "added")}})
    return record


def main(argv):
    parser = argparse.ArgumentParser(prog="data_guard.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="op", required=True)
    s = sub.add_parser("snapshot"); s.add_argument("dir"); s.add_argument("--reason", default="")
    s.add_argument("--accept-removed", type=int, default=0); s.add_argument("--accept-shrunk", type=int, default=0)
    s.add_argument("--accept-changed", type=int, default=0)
    c = sub.add_parser("check"); c.add_argument("dir")
    rw = sub.add_parser("record-write"); rw.add_argument("dir"); rw.add_argument("--reason", required=True)
    rw.add_argument("files", nargs="+")
    w = sub.add_parser("swap"); w.add_argument("--src", required=True); w.add_argument("--dst", required=True)
    w.add_argument("--reason", required=True); w.add_argument("--allow-removed", type=int, default=0)
    w.add_argument("--allow-shrunk", type=int, default=0)
    args = parser.parse_args(argv[1:])
    if args.op == "snapshot":
        rec = snapshot(args.dir, note=args.reason, accept_removed=args.accept_removed, accept_shrunk=args.accept_shrunk,
                       accept_changed=args.accept_changed)
        print(json.dumps({k: v for k, v in rec.items() if k != "entries"}))
        return 0
    if args.op == "record-write":
        print(json.dumps(record_write(args.dir, args.files, args.reason)))
        return 0
    if args.op == "check":
        problems = check(args.dir)
        print("\n".join(problems) if problems else f"{args.dir}: nothing removed, shrunk or rewritten since the last manifest")
        return 1 if problems else 0
    rec = swap(args.src, args.dst, args.reason, args.allow_removed, args.allow_shrunk)
    print(json.dumps({k: v for k, v in rec.items() if k != "diff"}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
