"""Commit and push the D2 Binance funding slice at a span of exactly 61 days.

Token comes from /opt/data/.env and is never printed. Only the files of this
slice are staged, so daemon edits sitting in the worktree do not ride along.
The remote is restored to the plain URL even if the push fails.
"""

import subprocess
from pathlib import Path

ROOT = Path("/opt/data/workspace/regime-tester")
PLAIN = "https://github.com/luke815/Hermes-Research.git"
ENV = Path("/opt/data/.env")
PATHS = [
    "scripts/d2_binance_funding.py",
    "scripts/push_d2_span61.py",
    "results/2026-11-15_d2_binance_funding_span61.json",
    "research/log.md",
    "research/backlog.md",
    "data/binance_funding/DDOGUSDT.csv",
    "data/binance_funding/GTLBUSDT.csv",
    "data/binance_funding/MDBUSDT.csv",
    "data/binance_funding/NVDLUSDT.csv",
    "data/binance_funding/TEAMUSDT.csv",
    "data/binance_funding/TSLLUSDT.csv",
    "data/binance_funding/ZSUSDT.csv",
]
MESSAGE = "D2 Binance per-venue funding, live names with a span of exactly 61 days: recorded, not admitted"


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
    authed = "https://x-access-token:" + secret + "@github.com/luke815/Hermes-Research.git"
    git("-c", "user.name=Hermes", "-c", "user.email=hermes@local", "add", "--", *PATHS)
    staged = git("diff", "--cached", "--name-only").stdout.strip().splitlines()
    unexpected = [p for p in staged if p not in PATHS]
    if unexpected:
        git("reset", "-q", "HEAD", "--", *unexpected, check=False)
        raise SystemExit(f"unexpected staged files: {unexpected}")
    if not staged:
        raise SystemExit("nothing staged")
    commit = git("-c", "user.name=Hermes", "--c", "user.email=hermes@local",
                 "commit", "-m", MESSAGE, check=False)
    print("commit_exit", commit.returncode)
    if commit.returncode != 0:
        print((commit.stderr or commit.stdout)[-400:])
        raise SystemExit(commit.returncode)
    print("commit", git("rev-parse", "HEAD").stdout.strip())
    try:
        git("remote", "set-url", "origin", authed)
        push = git("push", "origin", "HEAD:main", check=False)
        print("push_exit", push.returncode)
        text = ((push.stderr or "") + (push.stdout or "")).replace(secret, "[redacted]")
        print(text[-600:])
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
