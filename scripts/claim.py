"""One owner per backlog item. Take a claim before touching an item, release it after.

Two runs worked A1 at the same time on 2026-11-17 and overwrote each other's
results. A claim is a file in ops/claims/ created exclusively, so the second
taker sees the first and skips the item.

    python3 scripts/claim.py take A1 --owner cron            exit 0 taken (prints a secret), 3 held by someone else
    python3 scripts/claim.py touch A1 --owner cron --secret S  extend a claim you hold
    python3 scripts/claim.py release A1 --owner cron --secret S
    python3 scripts/claim.py release A1 --owner chat --force --reason "cron died at 03:10, see log"
    python3 scripts/claim.py status                           every claim with its age

take prints a one-time secret. touch and release need it, so a second run
cannot release a claim it does not hold by typing the owner's name. --force
and --steal work without the secret, need a --reason, and are listed by the
health check for the next 24 hours.

A claim expires after --ttl-hours (default 6, allowed 0.25 to 24) without a
touch, so a run that died does not block the item forever. Taking an expired
claim is recorded as a takeover and keeps the original work head, so
done_check still measures code changes from where the item was first begun.

Runs are many short processes, so a pid proves nothing here; the owner string,
the secret and the time do. Use "cron" for the scheduled research run and
"chat" for the interactive session.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import secrets
import socket
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLAIMS = os.path.join(ROOT, "ops", "claims")
LOG = os.path.join(ROOT, "ops", "claims.log")
DEFAULT_TTL_HOURS = 6.0
TTL_MIN, TTL_MAX = 0.25, 24.0
ITEM = re.compile(r"^[A-Z]{1,3}\d{1,3}[a-z]?$")
EPOCH = "1970-01-01T00:00:00Z"

HELD = 3


def _now():
    return datetime.now(timezone.utc)


def _stamp(when=None):
    return (when or _now()).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(stamp):
    try:
        return datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


def _head(root):
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=root, text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, OSError):
        return None


def _path(item, claims_dir):
    if not ITEM.match(item or ""):
        raise SystemExit(f"item {item!r} must look like A1, L12 or C9a (ASCII letters then digits)")
    return os.path.join(claims_dir, f"{item}.json")


def _log(line, log_path):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a") as handle:
        handle.write(f"{_stamp()} {line}\n")


def _digest(secret):
    return hashlib.sha256(secret.encode()).hexdigest()


def _write(path, record):
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w") as handle:
        json.dump(record, handle, indent=1)
    os.replace(tmp, path)


def read(item, claims_dir=CLAIMS):
    path = _path(item, claims_dir)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as handle:
            rec = json.load(handle)
        if not isinstance(rec, dict) or "owner" not in rec:
            raise ValueError("not a claim")
        return rec
    except (OSError, ValueError):
        # a corrupt claim is expired and visible, never a silent permanent hold
        return {"item": item, "owner": "?", "taken_at": EPOCH, "touched_at": EPOCH, "ttl_hours": DEFAULT_TTL_HOURS,
                "corrupt": True}


def age_hours(claim, now=None):
    return ((now or _now()) - _parse(claim.get("touched_at") or claim.get("taken_at"))).total_seconds() / 3600


def is_expired(claim, now=None):
    try:
        ttl = float(claim.get("ttl_hours", DEFAULT_TTL_HOURS))
    except (TypeError, ValueError):
        ttl = 0.0
    if not math.isfinite(ttl) or ttl <= 0:
        ttl = 0.0
    return age_hours(claim, now) > ttl


def _valid_ttl(ttl_hours):
    try:
        ttl = float(ttl_hours)
    except (TypeError, ValueError):
        ttl = float("nan")
    if not math.isfinite(ttl) or not TTL_MIN <= ttl <= TTL_MAX:
        raise SystemExit(f"--ttl-hours must be between {TTL_MIN} and {TTL_MAX}")
    return ttl


def take(item, owner, ttl_hours=DEFAULT_TTL_HOURS, steal=False, reason="", claims_dir=CLAIMS, log_path=LOG,
         root=ROOT, _retry=True):
    """Create the claim exclusively. Returns (exit_code, record_with_secret_or_holder)."""
    ttl = _valid_ttl(ttl_hours)
    if steal and len(reason.strip()) < 10:
        raise SystemExit("--steal needs --reason saying why a live claim is being broken")
    os.makedirs(claims_dir, exist_ok=True)
    path = _path(item, claims_dir)
    now = _now()
    secret = secrets.token_hex(8)
    record = {"item": item, "owner": owner, "host": socket.gethostname(), "pid": os.getpid(),
              "taken_at": _stamp(now), "touched_at": _stamp(now), "ttl_hours": ttl, "head": _head(root),
              "secret_sha256": _digest(secret)}
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        holder = read(item, claims_dir)
        if holder and not is_expired(holder, now) and not steal:
            _log(f"HELD {item} wanted by {owner}, held by {holder.get('owner')} since {holder.get('taken_at')}", log_path)
            return HELD, holder
        live = bool(holder and not is_expired(holder, now))
        why = "stole live claim" if live else "took over expired claim"
        # exactly one taker wins the rename; the loser retries and finds a fresh live claim
        try:
            os.rename(path, f"{path}.taken.{os.getpid()}")
        except FileNotFoundError:
            if not _retry:
                return HELD, read(item, claims_dir)
            return take(item, owner, ttl, steal, reason, claims_dir, log_path, root, _retry=False)
        try:
            os.remove(f"{path}.taken.{os.getpid()}")
        except OSError:
            pass
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            return HELD, read(item, claims_dir)
        record["took_over"] = {"from": {k: v for k, v in (holder or {}).items() if k != "secret_sha256"},
                               "reason": why, "note": reason}
        if holder and holder.get("head"):
            record["head"] = holder["head"]  # measure code changes from where the item was first begun
        with os.fdopen(fd, "w") as handle:
            json.dump(record, handle, indent=1)
        _log(f"TAKEOVER {item} by {owner} ({why}) from {holder and holder.get('owner')} ttl={ttl} {reason}".rstrip(),
             log_path)
        return 0, {**record, "secret": secret}
    with os.fdopen(fd, "w") as handle:
        json.dump(record, handle, indent=1)
    _log(f"TAKE {item} by {owner} ttl={ttl}", log_path)
    return 0, {**record, "secret": secret}


def _holds(holder, owner, secret):
    return bool(holder) and holder.get("owner") == owner and secret and holder.get("secret_sha256") == _digest(secret)


def touch(item, owner, secret=None, claims_dir=CLAIMS, log_path=LOG):
    holder = read(item, claims_dir)
    if not _holds(holder, owner, secret):
        return HELD, holder
    holder["touched_at"] = _stamp()
    _write(_path(item, claims_dir), holder)
    return 0, holder


def release(item, owner, secret=None, force=False, reason="", claims_dir=CLAIMS, log_path=LOG):
    holder = read(item, claims_dir)
    if not holder:
        return 0, None
    if not _holds(holder, owner, secret):
        if not force:
            _log(f"RELEASE-REFUSED {item} by {owner}, held by {holder.get('owner')}", log_path)
            return HELD, holder
        if len(reason.strip()) < 10:
            raise SystemExit("--force needs --reason saying why a claim you do not hold is being released")
    os.remove(_path(item, claims_dir))
    forced = not _holds(holder, owner, secret)
    _log(f"RELEASE {item} by {owner}" + (f" (forced) {reason}" if forced else ""), log_path)
    return 0, holder


def status(claims_dir=CLAIMS, now=None):
    out = []
    if not os.path.isdir(claims_dir):
        return out
    for name in sorted(os.listdir(claims_dir)):
        if not name.endswith(".json"):
            continue
        claim = read(name[:-5], claims_dir)
        if claim:
            claim = {k: v for k, v in claim.items() if k != "secret_sha256"}
            claim["age_hours"] = round(age_hours(claim, now), 2)
            claim["expired"] = is_expired(claim, now)
            out.append(claim)
    return out


def recent_events(log_path=LOG, hours=24, now=None):
    """Steals and forced releases in the last `hours`, for the health check."""
    out = []
    if not os.path.exists(log_path):
        return out
    cutoff = (now or _now()).timestamp() - hours * 3600
    with open(log_path) as handle:
        for line in handle:
            when = _parse(line[:20]).timestamp()
            if when >= cutoff and ("(stole live claim)" in line or "(forced)" in line):
                out.append(line.strip())
    return out


def main(argv):
    parser = argparse.ArgumentParser(prog="claim.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("op", choices=["take", "touch", "release", "status"])
    parser.add_argument("item", nargs="?")
    parser.add_argument("--owner")
    parser.add_argument("--secret")
    parser.add_argument("--ttl-hours", type=float, default=DEFAULT_TTL_HOURS)
    parser.add_argument("--steal", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--reason", default="")
    args = parser.parse_args(argv[1:])
    if args.op == "status":
        for claim in status():
            print(json.dumps(claim))
        return 0
    if not args.item or not args.owner:
        parser.error("item and --owner are required")
    if args.op == "take":
        code, record = take(args.item, args.owner, args.ttl_hours, steal=args.steal, reason=args.reason)
    elif args.op == "touch":
        code, record = touch(args.item, args.owner, args.secret)
    else:
        code, record = release(args.item, args.owner, args.secret, force=args.force, reason=args.reason)
    shown = {k: v for k, v in (record or {}).items() if k != "secret_sha256"}
    print(json.dumps({"op": args.op, "item": args.item, "ok": code == 0, "claim": shown}))
    if args.op == "take" and code == 0:
        print(f"keep this secret for touch and release: {record['secret']}")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
