"""Commit and push the 701 to 800 Bybit price slice. Token from env, never printed.

Remote is restored to the plain URL even if the push fails.
"""

import subprocess
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester")
PLAIN = "https://github.com/luke815/Hermes-Research.git"
ENV = Path("/opt/data/.env")
PATHS = [
    "scripts/bybit_prices_701_800.py",
    "scripts/bybit_reduce_pending.py",
    "scripts/push_d1_701_800.py",
    "results/2026-11-14_d1_bybit_prices_701_800.json",
    "research/log.md",
    "research/backlog.md",
]
MESSAGE = "D1 Bybit stopped-name prices, 701 to 800 listed days: recorded, not admitted"


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, check=check, capture_output=True, text=True)


def token() -> str:
    for line in ENV.read_text().splitlines():
        if line.startswith("GITHUB_TOKEN="):
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            if not value:
                raise SystemExit("GITHUB_TOKEN empty")
            return value
    raise SystemExit("GITHUB_TOKEN missing")


def main() -> None:
    secret = token()
    authed = f"https://x-access-token:{secret}@github.com/luke815/Hermes-Research.git"
    git("-c", "user.name=Hermes", "-c", "user.email=hermes@local", "add", "--", *PATHS)
    staged = git("diff", "--cached", "--name-only").stdout.strip().splitlines()
    unexpected = [p for p in staged if p not in PATHS]
    if unexpected:
        git("reset", "-q", "HEAD", "--", *unexpected, check=False)
        raise SystemExit(f"unexpected staged files: {unexpected}")
    if not staged:
        raise SystemExit("nothing staged")
    commit = git(
        "-c", "user.name=Hermes", "-c", "user.email=hermes@local",
        "commit", "-m", MESSAGE, check=False,
    )
    print("commit_exit", commit.returncode)
    if commit.returncode != 0:
        print((commit.stderr or commit.stdout)[-400:])
        raise SystemExit(commit.returncode)
    print("commit", git("rev-parse", "HEAD").stdout.strip())
    try:
        git("remote", "set-url", "origin", authed)
        push = git("push", "origin", "HEAD:main", check=False)
        print("push_exit", push.returncode)
        print(((push.stderr or "") + (push.stdout or "")).replace(secret, "[redacted]")[-600:])
        if push.returncode != 0:
            raise SystemExit(push.returncode)
    finally:
        git("remote", "set-url", "origin", PLAIN)
        url = git("remote", "get-url", "origin").stdout.strip()
        print("remote_plain", url == PLAIN)
        if secret in url:
            raise SystemExit("token left in remote")


if __name__ == "__main__":
    main()
